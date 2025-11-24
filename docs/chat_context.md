# Generative Genomics Sandbox — Project Context

## Purpose
This project trains a conditional VAE (CVAE) on GEO RNA-seq data (GSE60424) to
generate predicted gene expression profiles from experimental descriptors.

## Workflow
1. Raw GEO dataset downloaded into data/raw/
2. scripts/preprocess.py parses series matrix:
   - extracts metadata (celltype, diseasestatus, gender, smoker, age)
   - builds expression matrix
   - selects top 500 variable genes
   - applies log1p normalization
   - standardizes genes
   - one-hot encodes metadata
   - saves:
       data/processed/X_expr.npy
       data/processed/X_cond.npy
       data/processed/meta.csv
       models/genes_gse60424.json
       models/design_encoder_gse60424.pkl
       models/expr_scaler_gse60424.pkl
3. scripts/build_gene_mapping.py maps gene IDs to symbols using annotation data
   - saves: models/gene_names_gse60424.json
4. CVAE training loads these processed arrays (see notebooks/01_train_cvae.ipynb)
5. FastAPI model server loads trained CVAE weights and encoder/scaler
   and responds to POST /generate with gene records containing id, symbol, and expression.

## Architecture
- frontend: React / TypeScript + webpack, includes volcano plot visualization
- gateway: Go HTTP proxy, serves static frontend and proxies API requests
- model: FastAPI + PyTorch, returns gene expression with symbols
- deployment: Docker multi-stage build, AWS ECS deployment scripts available
