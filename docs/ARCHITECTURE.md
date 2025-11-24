Architecture (current demo):
- React + TypeScript SPA (built with webpack) served as static assets by the Go gateway
  - Includes volcano plot visualization component using Plotly.js
  - Displays gene expression results with gene symbols and IDs
- Go API Gateway
  - Serves `/api/health`
  - Proxies `/api/generate` to the model server
  - Serves `index.html` + hashed JS bundles from `/app/web-client-dist`
- FastAPI Model Server (Python + PyTorch)
  - `/health` returns status + model version
  - `/generate` loads artifacts (genes, encoder, scaler, CVAE weights) and returns ~500-gene expression records
  - Maps gene IDs to symbols using `models/gene_names_gse60424.json`

Notes:
- Dockerfile builds Go binary, React dist, and Python runtime into a single image.
- Model artifacts live under `models/` and preprocessed data under `data/processed/`.
- Entrypoint script handles process cleanup with signal handling to prevent zombie processes.
- Deployment scripts available in `deploy/` for AWS ECS infrastructure.
