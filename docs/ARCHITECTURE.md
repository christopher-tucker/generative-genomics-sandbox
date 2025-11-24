Architecture (current demo):
- React + TypeScript SPA (built with webpack) served as static assets by the Go gateway
- Go API Gateway
  - Serves `/api/health`
  - Proxies `/api/generate` to the model server
  - Serves `index.html` + hashed JS bundles from `/app/web-client-dist`
- FastAPI Model Server (Python + PyTorch)
  - `/health` returns status + model version
  - `/generate` loads artifacts (genes, encoder, scaler, CVAE weights) and returns ~500-gene expression vector

Notes:
- Dockerfile builds Go binary, React dist, and Python runtime into a single image.
- Model artifacts live under `models/` and preprocessed data under `data/processed/`.
