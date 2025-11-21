"""
Preprocess GSE102901 GEO series matrix into ML-ready matrices.

Steps:
- Load series matrix file from data/raw/
- Parse sample metadata (cell_type, treatment, etc.)
- Build expression matrix (samples x genes)
- Log-transform and select top N most variable genes
- Standardize expression values
- One-hot encode metadata into design matrix
- Save:
    data/processed/X_expr.npy
    data/processed/X_cond.npy
    data/processed/meta.csv
    models/genes_gse102901.json
    models/design_encoder_gse102901.pkl
    models/expr_scaler_gse102901.pkl
"""

import os
import json
import gzip
from io import StringIO

import numpy as np
import pandas as pd
from sklearn.preprocessing import OneHotEncoder, StandardScaler
import joblib


RAW_DIR = os.path.join("data", "raw")
PROCESSED_DIR = os.path.join("data", "processed")
MODELS_DIR = "models"

# Default file name we expect
DEFAULT_SERIES_BASENAME = "GSE102901_series_matrix.txt"

# Number of genes to keep (most variable)
N_GENES = 500

# Candidate metadata fields to use as conditioning variables
CANDIDATE_COND_FIELDS = [
    "cell_type",
    "cell line",
    "treatment",
    "timepoint",
    "time_point",
    "dose",
    "concentration",
]


def _open_series_file():
    """
    Try opening:
      data/raw/GSE102901_series_matrix.txt
    or
      data/raw/GSE102901_series_matrix.txt.gz
    """
    txt_path = os.path.join(RAW_DIR, DEFAULT_SERIES_BASENAME)
    gz_path = txt_path + ".gz"

    if os.path.exists(txt_path):
        print(f"Loading series matrix from {txt_path}")
        return open(txt_path, "r"), txt_path
    elif os.path.exists(gz_path):
        print(f"Loading series matrix from {gz_path}")
        return gzip.open(gz_path, "rt"), gz_path
    else:
        raise FileNotFoundError(
            f"Could not find {txt_path} or {gz_path}. "
            "Make sure you downloaded the GEO series matrix file "
            "into data/raw/."
        )


def load_series_matrix_lines():
    f, path = _open_series_file()
    with f:
        lines = f.readlines()
    print(f"Loaded {len(lines)} lines from {path}")
    return lines


def parse_sample_metadata(lines):
    """
    Parse GEO series matrix lines to extract sample IDs and metadata.
    Returns:
        meta_df: pandas DataFrame indexed by sample_id
    """
    sample_ids = []
    characteristics = {}

    # 1) Find sample IDs from !Sample_geo_accession line
    for line in lines:
        if line.startswith("!Sample_geo_accession"):
            parts = line.strip().split("\t")
            sample_ids = [sid.strip().strip('"') for sid in parts[1:]]
            for sid in sample_ids:
                characteristics[sid] = {}
            break

    if not sample_ids:
        raise RuntimeError("Could not find !Sample_geo_accession line in series matrix.")

    print(f"Found {len(sample_ids)} samples")

    # 2) Parse characteristics
    field_idx = 0
    for line in lines:
        if line.startswith("!Sample_characteristics_ch1"):
            parts = line.rstrip("\n").split("\t")
            header_cell = parts[0]
            values = [v.strip().strip('"') for v in parts[1:]]

            # Try to infer the field name from the header or first value
            field = None
            if "=" in header_cell:
                meta_header = header_cell.split("=", 1)[1].strip()
                if ":" in meta_header:
                    field = meta_header.split(":", 1)[0].strip()
                else:
                    field = meta_header.strip()
            else:
                first_val = values[0] if values else ""
                if ":" in first_val:
                    field = first_val.split(":", 1)[0].strip()

            if not field:
                field_idx += 1
                field = f"characteristics_ch1_{field_idx}"

            field = field.lower().replace(" ", "_")

            for sid, val in zip(sample_ids, values):
                v = val.strip()
                # Many values also look like "cell type: MCF7"; keep part after ':'
                if ":" in v:
                    v = v.split(":", 1)[1].strip()
                characteristics[sid][field] = v

    # 3) Build DataFrame
    rows = []
    for sid in sample_ids:
        row = {"sample_id": sid}
        row.update(characteristics.get(sid, {}))
        rows.append(row)

    meta_df = pd.DataFrame(rows).set_index("sample_id")
    print("Metadata columns:", list(meta_df.columns))
    return meta_df


def parse_expression_matrix(lines, sample_ids):
    """
    Find the expression table (starting at ID_REF) and return a
    DataFrame of shape [samples x genes].
    """
    data_start_idx = None
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        if stripped.startswith("ID_REF") or stripped.startswith('"ID_REF"'):
            data_start_idx = i
            break

    if data_start_idx is None:
        raise RuntimeError("Could not find expression table header (ID_REF).")

    print(f"Expression table starts at line {data_start_idx}")

    data_str = "".join(lines[data_start_idx:])
    expr_df = pd.read_csv(StringIO(data_str), sep="\t")

    # ID_REF column = gene identifiers
    expr_df = expr_df.rename(columns={"ID_REF": "gene_id"})
    expr_df = expr_df.set_index("gene_id")

    # transpose -> samples x genes
    expr_df = expr_df.transpose()
    expr_df.index.name = "sample_id"

    # Keep only the sample_ids we saw in metadata, in order
    expr_df = expr_df.loc[sample_ids]

    print("Expression matrix shape (samples x genes):", expr_df.shape)
    return expr_df


def select_conditioning_fields(meta_df):
    """
    Choose metadata fields to use for conditioning based on availability.
    """
    normalized_cols = {c.lower().strip(): c for c in meta_df.columns}
    chosen = []

    for candidate in CANDIDATE_COND_FIELDS:
        cand_norm = candidate.lower().strip()
        if cand_norm in normalized_cols:
            chosen.append(normalized_cols[cand_norm])

    if not chosen:
        # If nothing matched, just take all columns as a fallback
        chosen = list(meta_df.columns)
        print("No candidate conditioning fields found explicitly.")
        print("Falling back to using all metadata columns.")
    else:
        print("Using conditioning fields:", chosen)

    return chosen


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    # 1) Load raw lines
    lines = load_series_matrix_lines()

    # 2) Parse metadata and expression
    meta_df = parse_sample_metadata(lines)
    sample_ids = list(meta_df.index)
    expr_df = parse_expression_matrix(lines, sample_ids)

    # Convert expression to float matrix
    expr = expr_df.astype(float)

    # 3) Log1p-normalize expression
    expr_log = np.log1p(expr)
    print("Expression after log1p shape:", expr_log.shape)

    # 4) Select top N most variable genes
    gene_var = expr_log.var(axis=0)
    top_genes = gene_var.sort_values(ascending=False).head(N_GENES).index
    expr_log_top = expr_log[top_genes]
    print(f"Selected top {N_GENES} most variable genes. New shape:", expr_log_top.shape)

    # 5) Standardize expression (per-gene)
    expr_scaler = StandardScaler()
    X_expr = expr_scaler.fit_transform(expr_log_top.values)  # samples x genes
    X_expr = X_expr.astype("float32")

    # 6) Build conditioning matrix from metadata
    cond_fields = select_conditioning_fields(meta_df)
    cond_df = meta_df[cond_fields].copy()

    # Ensure all fields are strings (for OneHotEncoder)
    for c in cond_fields:
        cond_df[c] = cond_df[c].astype(str)

    from sklearn.preprocessing import OneHotEncoder
    try:
        cond_encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    except TypeError:
        # sklearn <1.2 uses `sparse` instead of `sparse_output`
        cond_encoder = OneHotEncoder(sparse=False, handle_unknown="ignore")
    X_cond = cond_encoder.fit_transform(cond_df.values).astype("float32")

    print("Conditioning matrix shape (samples x cond_dim):", X_cond.shape)

    # 7) Save processed arrays
    x_expr_path = os.path.join(PROCESSED_DIR, "X_expr.npy")
    x_cond_path = os.path.join(PROCESSED_DIR, "X_cond.npy")
    meta_path = os.path.join(PROCESSED_DIR, "meta.csv")

    np.save(x_expr_path, X_expr)
    np.save(x_cond_path, X_cond)
    meta_df.to_csv(meta_path)

    print(f"Saved X_expr to {x_expr_path}")
    print(f"Saved X_cond to {x_cond_path}")
    print(f"Saved metadata to {meta_path}")

    # 8) Save model-related artifacts
    genes = list(top_genes)
    genes_path = os.path.join(MODELS_DIR, "genes_gse102901.json")
    design_encoder_path = os.path.join(MODELS_DIR, "design_encoder_gse102901.pkl")
    expr_scaler_path = os.path.join(MODELS_DIR, "expr_scaler_gse102901.pkl")

    with open(genes_path, "w") as f:
        json.dump(genes, f)

    joblib.dump(cond_encoder, design_encoder_path)
    joblib.dump(expr_scaler, expr_scaler_path)

    print(f"Saved genes list to {genes_path}")
    print(f"Saved design encoder to {design_encoder_path}")
    print(f"Saved expr scaler to {expr_scaler_path}")

    print("Preprocessing complete.")


if __name__ == "__main__":
    main()
