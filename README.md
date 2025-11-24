# Generative Genomics Sandbox

A minimal generative genomics platform that predicts gene expression from biological experiment descriptions.

## Overview

This project builds a tiny version of a generative genomics platform that:

1. Takes a biological experiment description as input
2. Passes it through an AI model to generate a predicted gene expression vector (~500 genes)
3. Serves predictions through a FastAPI backend
4. Proxies requests through a Go API Gateway
5. Visualizes results in a React frontend (React + TypeScript + webpack)

### Example Input

```
- Cell line: MCF7 cells
- Treatment: estradiol
- Dose: 10
- Timepoint: 24 hours
```

**Real-world inspiration:** Platforms like Synthesize Bio or Dyno Therapeutics.

## Tech Stack

- **Model server:** FastAPI + PyTorch (serves `/health` and `/generate`)
- **API Gateway:** Golang (proxies `/api/generate` to the model server and serves static frontend)
- **Frontend:** React + TypeScript + webpack (dev server on :3000; built assets served by gateway)
- **Deployment:** Dockerfile builds Go binary + React dist + Python runtime

## Data Sources

- **GSE60424** (NCBI GEO): Series matrix + TPM counts (GRCh38.p13) from https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE60424
- **GSE113764** (NCBI GEO): Series matrix only, kept as an additional small example

## Documentation

See `docs/` for architecture and API specifications.

## Local development

### Model server (FastAPI)
```bash
cd services/model_server
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```
Health check: `curl http://localhost:8001/health`

### Frontend (webpack dev server)
```bash
cd web-client
npm install
npm start   # serves on http://localhost:3000 and proxies /api to :8080
```

### API Gateway (Go)
```bash
cd services/api_gateway
go run ./cmd/gateway   # listens on :8080, expects model server at :8001
```

### Docker (all-in-one)
Builds Go binary, React dist, and Python runtime:
```bash
docker build -t gg-app .
docker run --rm -p 8080:8080 gg-app   # gateway + model server; frontend served from /app/web-client-dist
```

## Tests

- Model server unit tests: `cd services/model_server && pytest app/tests -q`
- API gateway tests: `cd services/api_gateway && go test ./...`

## Preprocessing

Run `python scripts/preprocess.py` to convert the GEO data in `data/raw/` into training-ready tensors:

- Inputs: `data/raw/GSE60424_series_matrix.txt(.gz)` and `data/raw/GSE60424_norm_counts_TPM_GRCh38.p13_NCBI.tsv.gz`
- Outputs: `data/processed/X_expr.npy`, `data/processed/X_cond.npy`, `data/processed/meta.csv`
- Saved artifacts: `models/genes_gse60424.json`, `models/design_encoder_gse60424.pkl`, `models/expr_scaler_gse60424.pkl`
