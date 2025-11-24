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
  "genes": [
    {
      "id": 6279,
      "symbol": "S100A8",
      "expression": 4.7647948265
    },
    {
      "id": 6280,
      "symbol": "S100A9",
      "expression": 5.9913253784
    }
    // ... ~500 gene records total
  ]
}
```

Each gene record contains:
- `id`: Numeric gene ID (Entrez Gene ID)
- `symbol`: Gene symbol (e.g., "S100A8", "CD4") mapped from `models/gene_names_gse60424.json`
- `expression`: Expression value (float, inverse-scaled log1p space)
