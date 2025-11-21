# Generative Genomics Sandbox

A minimal generative genomics platform that predicts gene expression from biological experiment descriptions.

## Overview

This project builds a tiny version of a generative genomics platform that:

1. Takes a biological experiment description as input
2. Passes it through an AI model to generate a predicted gene expression vector (~500 genes)
3. Serves predictions through a FastAPI backend
4. Proxies requests through a Go API Gateway
5. Visualizes results in a React frontend

### Example Input

```
- Cell line: MCF7 cells
- Treatment: estradiol
- Dose: 10
- Timepoint: 24 hours
```

**Real-world inspiration:** Platforms like Synthesize Bio or Dyno Therapeutics.

## Tech Stack

- **Backend:** FastAPI model server (Python + PyTorch)
- **API Gateway:** Golang
- **Frontend:** React + TypeScript
- **Database:** SQLite / Postgres (dev)
- **Deployment:** Docker Compose for local demo

## Data Sources

- **GSE60424** (NCBI GEO): Series matrix + TPM counts (GRCh38.p13) from https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE60424
- **GSE113764** (NCBI GEO): Series matrix only, kept as an additional small example

## Documentation

See `docs/` for architecture and API specifications.

## Preprocessing

Run `python scripts/preprocess.py` to convert the GEO data in `data/raw/` into training-ready tensors:

- Inputs: `data/raw/GSE60424_series_matrix.txt(.gz)` and `data/raw/GSE60424_norm_counts_TPM_GRCh38.p13_NCBI.tsv.gz`
- Outputs: `data/processed/X_expr.npy`, `data/processed/X_cond.npy`, `data/processed/meta.csv`
- Saved artifacts: `models/genes_gse60424.json`, `models/design_encoder_gse60424.pkl`, `models/expr_scaler_gse60424.pkl`
