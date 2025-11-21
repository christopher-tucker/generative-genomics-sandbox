"""
Preprocess GSE60424 GEO data into ML-ready matrices.

We use:
- Series Matrix file       -> sample metadata (conditions, cell types, etc.)
- NCBI TPM counts matrix   -> gene expression matrix (genes x samples)

Steps:
- Load series matrix from data/raw/GSE60424_series_matrix.txt(.gz)
- Parse sample metadata (individual, cell type, etc.)
- Load TPM counts table from data/raw/GSE60424_norm_counts_TPM_GRCh38.p13_NCBI.tsv.gz
- Align samples between metadata and expression
- Log-transform and select top N most variable genes
- Standardize expression values
- One-hot encode selected metadata columns into conditioning matrix
- Save:
    data/processed/X_expr.npy
    data/processed/X_cond.npy
    data/processed/meta.csv
    models/genes_gse60424.json
    models/design_encoder_gse60424.pkl
    models/expr_scaler_gse60424.pkl
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

# File names we expect
SERIES_BASENAME = "GSE60424_series_matrix.txt"
TPM_COUNTS_BASENAME = "GSE60424_norm_counts_TPM_GRCh38.p13_NCBI.tsv.gz"

# Number of genes to keep (most variable)
N_GENES = 500

# Candidate metadata fields to use as conditioning variables
CANDIDATE_COND_FIELDS = [
    "cell_type",
    "cell type",
    "tissue",
    "treatment",
    "timepoint",
    "time_point",
    "stimulus",
    "condition",
    "individual",
]


def _open_series_file():
    """
    Try opening:
      data/raw/GSE60424_series_matrix.txt
    or
      data/raw/GSE60424_series_matrix.txt.gz
    """
    txt_path = os.path.join(RAW_DIR, SERIES_BASENAME)
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
            "Make sure you downloaded the GEO Series Matrix file into data/raw/."
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
        meta_df: pandas DataFrame indexed by sample_id (GSM accession)
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

    print(f"Found {len(sample_ids)} samples in metadata")

    # 2) Parse characteristics lines
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


def load_tpm_expression(sample_ids):
    """
    Load NCBI TPM expression matrix from data/raw/GSE60424_norm_counts_TPM_GRCh38.p13_NCBI.tsv.gz

    Expected format:
    - first column: gene_id
    - remaining columns: sample IDs (ideally GSM accession numbers)
    """
    expr_path = os.path.join(RAW_DIR, TPM_COUNTS_BASENAME)
    if not os.path.exists(expr_path):
        raise FileNotFoundError(
            f"Could not find TPM counts file at {expr_path}. "
            "Make sure you downloaded GSE60424_norm_counts_TPM_GRCh38.p13_NCBI.tsv.gz into data/raw/."
        )

    print(f"Loading TPM expression matrix from {expr_path}")
    expr_df = pd.read_csv(expr_path, sep="\t")

    # First column = gene identifier
    gene_col = expr_df.columns[0]
    expr_df = expr_df.set_index(gene_col)

    # Columns are sample IDs; intersect with metadata sample IDs
    all_expr_samples = list(expr_df.columns)
    common = [sid for sid in sample_ids if sid in all_expr_samples]

    if not common:
        raise RuntimeError(
            "No overlapping sample IDs between metadata and expression matrix. "
            f"Metadata IDs (first 5): {sample_ids[:5]}, "
            f"expression IDs (first 5): {all_expr_samples[:5]}"
        )

    if len(common) < len(sample_ids):
        print(f"Warning: only {len(common)} / {len(sample_ids)} metadata samples "
              "found in expression matrix. Using the intersection.")

    # Subset and transpose -> samples x genes
    expr_df = expr_df[common].transpose()
    expr_df.index.name = "sample_id"

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
        chosen = list(meta_df.columns)
        print("No candidate conditioning fields found explicitly.")
        print("Falling back to using all metadata columns.")
    else:
        print("Using conditioning fields:", chosen)

    return chosen


def main():
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    os.makedirs(MODELS_DIR, exist_ok=True)

    # 1) Load series matrix lines and parse metadata
    lines = load_series_matrix_lines()
    meta_df = parse_sample_metadata(lines)
    sample_ids = list(meta_df.index)

    # 2) Load TPM expression matrix and align with metadata
    expr_df = load_tpm_expression(sample_ids)

    # Align order
    common_ids = expr_df.index.intersection(meta_df.index)
    expr_df = expr_df.loc[common_ids]
    meta_df = meta_df.loc[common_ids]
    print(f"After aligning, we have {expr_df.shape[0]} samples")

    # 3) Convert expression to float and log1p-normalize
    expr = expr_df.astype(float)
    expr_log = np.log1p(expr)
    print("Expression after log1p shape:", expr_log.shape)

    # 4) Select top N most variable genes
    gene_var = expr_log.var(axis=0)
    top_genes = gene_var.sort_values(ascending=False).head(N_GENES).index
    expr_log_top = expr_log[top_genes]
    print(f"Selected top {min(N_GENES, expr_log_top.shape[1])} most variable genes. "
          f"New shape: {expr_log_top.shape}")

    # 5) Standardize expression (per-gene)
    expr_scaler = StandardScaler()
    X_expr = expr_scaler.fit_transform(expr_log_top.values)  # samples x genes
    X_expr = X_expr.astype("float32")

    # 6) Build conditioning matrix from metadata
    cond_fields = select_conditioning_fields(meta_df)
    cond_df = meta_df[cond_fields].copy()

    for c in cond_fields:
        cond_df[c] = cond_df[c].astype(str)

    try:
        cond_encoder = OneHotEncoder(sparse_output=False, handle_unknown="ignore")
    except TypeError:
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
    genes_path = os.path.join(MODELS_DIR, "genes_gse60424.json")
    design_encoder_path = os.path.join(MODELS_DIR, "design_encoder_gse60424.pkl")
    expr_scaler_path = os.path.join(MODELS_DIR, "expr_scaler_gse60424.pkl")

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
