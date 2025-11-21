from fastapi import FastAPI
from pydantic import BaseModel
from .inference import generate_dummy

app = FastAPI()

class Descriptor(BaseModel):
    cell_type: str
    treatment: str
    dose: float
    timepoint: float

@app.get('/health')
def health():
    return {'status': 'ok', 'model_version': 'v0.1'}

@app.post('/generate')
def generate(descriptor: Descriptor):
    genes, expr = generate_dummy(descriptor.dict())
    return {'model_version': 'v0.1', 'genes': genes, 'expression': expr}
