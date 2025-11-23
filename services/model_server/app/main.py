from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel

from .inference import generate_expression, MODEL_VERSION

app = FastAPI(title="Generative Genomics Model Server")


class GenerateRequest(BaseModel):
    descriptor: Dict[str, Any]
    seed: Optional[int] = None


@app.get("/health")
def health():
    return {"status": "ok", "model_version": MODEL_VERSION}


@app.post("/generate")
def generate(req: GenerateRequest):
    genes, expr, model_version = generate_expression(req.descriptor, seed=req.seed)
    return {
        "model_version": model_version,
        "genes": genes,
        "expression": expr,
    }
