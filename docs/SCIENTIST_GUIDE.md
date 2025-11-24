Scientist guide (demo defaults):

- Inputs (descriptor keys): `celltype`, `diseasestatus`, `gender`, `smoker`, `age` (free text; matched case-insensitively to metadata columns).
- Output: ~500 gene records, each containing:
  - `id`: Numeric gene ID (Entrez Gene ID)
  - `symbol`: Gene symbol (e.g., "S100A8", "CD4", "IL2") mapped from annotation data
  - `expression`: Expression value (float, inverse-transformed log1p(normalized) space)
- Seed: optional integer for reproducible sampling (same seed produces same expression profile).
- Visualization: Frontend includes a volcano-style plot showing centered expression vs. deviation from mean.
- Limitations: toy CVAE trained on GSE60424; outputs are synthetic and should not be used for clinical/experimental decisions.
