API surface (through Go gateway):

- `GET /api/health` — gateway health
- `POST /api/generate` — proxy to model server `/generate`

Model server endpoints (FastAPI):

- `GET /health` — returns `{"status": "ok", "model_version": "cvae_gse60424_v1"}`
- `POST /generate`

Request body (example):
```json
{
  "descriptor": {
    "celltype": "CD4 T cells",
    "diseasestatus": "healthy",
    "gender": "female",
    "smoker": "no",
    "age": "45"
  },
  "seed": 42
}
```

Response body:
```json
{
  "model_version": "cvae_gse60424_v1",
  "genes": ["ENSG00000112357", "..."],
  "expression": [4.76, 5.99, ...]  // ~500 floats, inverse-scaled log1p space
}
```
