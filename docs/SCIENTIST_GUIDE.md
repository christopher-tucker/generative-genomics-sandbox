Scientist guide (demo defaults):

- Inputs (descriptor keys): `celltype`, `diseasestatus`, `gender`, `smoker`, `age` (free text; matched case-insensitively to metadata columns).
- Output: ~500 genes (IDs from `models/genes_gse60424.json`) with expression values in inverse-transformed log1p(normalized) space (floats).
- Seed: optional integer for reproducible sampling.
- Limitations: toy CVAE trained on GSE60424; outputs are synthetic and should not be used for clinical/experimental decisions.
