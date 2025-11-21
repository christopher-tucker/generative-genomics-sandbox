# Generative Genomics Sandbox — Project Context

## Purpose
This project trains a conditional VAE (CVAE) on GEO RNA-seq data (GSE102901) to
generate predicted gene expression profiles from experimental descriptors.

## Workflow
1. Raw GEO dataset downloaded into data/raw/
2. scripts/preprocess.py parses series matrix:
   - extracts metadata (treatment, cell_type…)
   - builds expression matrix
   - selects top 500 variable genes
   - applies log1p normalization
   - standardizes genes
   - one-hot encodes metadata
   - saves:
       data/processed/X_expr.npy
       data/processed/X_cond.npy
       models/*.pkl, *.json
3. CVAE training will load these processed arrays
4. FastAPI model server will load trained CVAE weights and encoder/scaler
   and respond to POST /generate with a predicted expression vector.

## Architecture
- frontend: React / TypeScript
- gateway: Go HTTP proxy
- model: FastAPI + PyTorch
