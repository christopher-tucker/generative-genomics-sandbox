import os
import json
import pandas as pd

ANNOT_PATH = os.path.join("data", "raw", "Human.GRCh38.p13.annot.tsv")
GENE_LIST_PATH = os.path.join("models", "genes_gse60424.json")
OUTPUT_PATH = os.path.join("models", "gene_names_gse60424.json")


def main():
    print(f"Loading annotation from: {ANNOT_PATH}")
    df = pd.read_csv(
        ANNOT_PATH,
        sep="\t",
        dtype={"GeneID": str, "Symbol": str},
    )
    print("Annotation columns:", list(df.columns))

    with open(GENE_LIST_PATH, "r") as f:
        gene_ids = json.load(f)

    # Build a lookup table: GeneID -> Symbol
    annot_map = {row["GeneID"]: row["Symbol"] for _, row in df.iterrows()}

    mapping = {}
    missing = 0

    for gid in gene_ids:
        symbol = annot_map.get(str(gid))
        if symbol is None or symbol == "":
            mapping[gid] = gid  # fallback: keep numeric ID
            missing += 1
        else:
            mapping[gid] = symbol

    print(f"Built mapping for {len(mapping)} genes (missing symbols for {missing})")

    os.makedirs("models", exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(mapping, f, indent=2)

    print(f"Saved gene name mapping to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
