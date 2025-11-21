POST /generate
Request:
{
  "descriptor": {
    "cell_type": "HEK293",
    "treatment": "drugX",
    "dose": 10,
    "timepoint": 24
  }
}
Response:
{
  "model_version": "v0.1",
  "genes": ["GENE1","GENE2",...],
  "expression": [0.12, 5.3, ...]
}
