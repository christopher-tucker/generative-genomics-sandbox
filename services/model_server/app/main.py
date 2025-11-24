import json
import os
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from .inference import generate_expression, MODEL_VERSION

app = FastAPI(title="Generative Genomics Model Server")

# Load gene ID -> symbol mapping (if available)
# Use same path resolution as inference.py
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "..", "..", "..", "models")

GENE_NAME_MAP: Dict[str, str] = {}
mapping_path = os.path.join(MODELS_DIR, "gene_names_gse60424.json")
if os.path.exists(mapping_path):
    with open(mapping_path, "r") as f:
        GENE_NAME_MAP = json.load(f)

class GenerateRequest(BaseModel):
    descriptor: Dict[str, Any]
    seed: Optional[int] = None


@app.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/generate")
def generate(req: GenerateRequest):
    gene_ids, expr_values, model_version = generate_expression(
        req.descriptor, seed=req.seed
    )

    genes_payload = []
    for gid, val in zip(gene_ids, expr_values):
        # Convert gid to string for lookup since GENE_NAME_MAP keys are strings
        symbol = GENE_NAME_MAP.get(str(gid), gid)
        genes_payload.append(
            {
                "id": gid,
                "symbol": symbol,
                "expression": float(val),
            }
        )

    return {
        "model_version": model_version,
        "genes": genes_payload,
    }