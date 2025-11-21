# Generative Genomics Sandbox

## 1. Goal

This project is a **toy generative genomics system**:

- Train a **conditional generative model** (Conditional VAE / CVAE) on RNA-seq gene expression data.
- The model learns to map from **experimental design descriptors** (e.g. cell type, treatment, dose, timepoint) to **predicted gene expression profiles**.
- Serve the model behind a **FastAPI service** and **Golang API gateway**.
- Expose a simple **React/TypeScript UI** where a user can define an experiment and visualize the generated expression.

This is intentionally a small-scale, educational version of real “generative genomics” platforms (e.g., predicting RNA-seq in silico).

---

## 2. Domain TL;DR

- We work with **bulk RNA-seq** data: each sample has expression values for many genes.
- The key objects:
  - **Samples**: e.g. “MCF7 cells treated with Drug X at 24h, dose 10µM”.
  - **Expression vector**: 1 row per sample, ~thousands of genes as columns.
  - **Design descriptor**: structured info about the sample (cell type, treatment, dose, timepoint, etc.).

The model’s job:  
> Given a *design descriptor*, generate a plausible *expression vector*.

---

## 3. Data

### Source

- Dataset: **GSE102901** from NCBI GEO (Gene Expression Omnibus).
- File used: `GSE102901_series_matrix.txt` (or `.txt.gz`) placed in `data/raw/`.

### Raw layout

- Top of the file: metadata lines starting with `!` and `^`.
- Sample IDs: from `!Sample_geo_accession` line.
- Sample metadata: from multiple `!Sample_characteristics_ch1` lines (e.g. `cell type`, `treatment`, etc.).
- Expression table: starts at the `ID_REF` line.
  - Rows: genes (`ID_REF`).
  - Columns: samples (GSM IDs).
  - Values: expression intensities / counts.

---

## 4. Preprocessing pipeline

Implemented (or planned) in `scripts/preprocess.py`.

Steps:

1. **Load series matrix**
   - Look for `data/raw/GSE102901_series_matrix.txt` or `.txt.gz`.
   - Read all lines into memory.

2. **Extract sample metadata**
   - Parse `!Sample_geo_accession` → list of sample IDs.
   - Parse `!Sample_characteristics_ch1` lines:
     - Normalize keys (e.g. `"cell type"` → `cell_type`).
     - Extract values (e.g. `"cell type: MCF7"` → `"MCF7"`).
   - Build `meta_df` (Pandas DataFrame) indexed by `sample_id`.

3. **Build expression matrix**
   - Find line starting with `ID_REF`.
   - Read expression table from that line onward with `pandas.read_csv`.
   - Use `ID_REF` as `gene_id`, set as index, then **transpose** so:
     - rows = samples
     - columns = genes
   - Align rows with `meta_df` sample IDs.

4. **Normalize and reduce genes**
   - Convert expression to `float`.
   - Apply **log1p** transform: `log(1 + x)`.
   - Compute per-gene variance across samples.
   - Keep top **N_GENES = 500** most variable genes.
   - Fit a `StandardScaler` per gene (zero mean, unit variance).
   - Result: `X_expr` of shape `[num_samples x num_genes]` as `float32`.

5. **Build conditioning (design) matrix**
   - Candidate conditioning fields: `["cell_type", "cell line", "treatment", "timepoint", "time_point", "dose", "concentration"]`.
   - Use the subset of these that exist in `meta_df`.
   - Convert chosen columns to strings.
   - Fit a `OneHotEncoder` (`sparse=False`, `handle_unknown="ignore"`).
   - Result: `X_cond` of shape `[num_samples x cond_dim]` as `float32`.

6. **Save processed artifacts**

To disk:

- `data/processed/X_expr.npy` — normalized expression (samples x selected genes).
- `data/processed/X_cond.npy` — one-hot encoded design descriptors.
- `data/processed/meta.csv` — metadata per sample.
- `models/genes_gse102901.json` — ordered list of selected gene IDs.
- `models/design_encoder_gse102901.pkl` — fitted `OneHotEncoder`.
- `models/expr_scaler_gse102901.pkl` — fitted `StandardScaler`.

These files are the input to the training code.

---

## 5. Model: Conditional VAE (CVAE)

Planned/typical structure in PyTorch:

- **Inputs:**
  - `x_expr`: expression vector (dim = `expr_dim`).
  - `x_cond`: design vector (dim = `cond_dim`).

- **Encoder:**
  - Concatenate `[x_expr, x_cond]`.
  - Feed through MLP → `hidden_dim`.
  - Predict `mu` and `logvar` for latent `z` (dim = `latent_dim`).

- **Reparameterization:**
  - `z = mu + eps * exp(0.5 * logvar)`.

- **Decoder:**
  - Concatenate `[z, x_cond]`.
  - Feed through MLP → reconstructed expression vector (`expr_dim`).

- **Loss:**
  - Reconstruction loss: MSE between reconstructed and original expression.
  - KL divergence between `q(z|x)` and `N(0, I)`.
  - Combined VAE loss = `(recon_loss + KL) / batch_size`.

Training loop:

- Load `X_expr` / `X_cond` from `data/processed`.
- Split into train/val.
- Train for N epochs, log train/val loss.
- Save model weights and training artifacts into `models/`.

Example artifacts:

- `models/cvae_gse102901_v0.pt` — `state_dict` for the CVAE.
- (Reuse `genes_gse102901.json`, `design_encoder_gse102901.pkl`, `expr_scaler_gse102901.pkl` from preprocessing.)

---

## 6. Serving architecture

### FastAPI model server (`services/model_server`)

Responsibilities:

- Load:
  - `cvae_gse102901_v0.pt` (PyTorch model).
  - `genes_gse102901.json`.
  - `design_encoder_gse102901.pkl`.
  - `expr_scaler_gse102901.pkl`.
- Expose:
  - `GET /health` — health status and model version.
  - `POST /generate` — body includes a design descriptor:
    ```json
    {
      "descriptor": {
        "cell_type": "MCF7",
        "treatment": "drugX",
        "dose": 10,
        "timepoint": 24
      }
    }
    ```
  - Pipeline in `/generate`:
    1. Convert descriptor to a one-row DataFrame.
    2. Apply `design_encoder.transform()` → `X_cond` row.
    3. Sample latent `z ~ N(0, I)`.
    4. Run `decoder(z, X_cond)` → predicted expression (scaled space).
    5. Apply `expr_scaler.inverse_transform()` to map back to normalized/log space.
    6. Return JSON:
       ```json
       {
         "model_version": "v0.1",
         "genes": [...],
         "expression": [...]
       }
       ```

### Golang API gateway (`services/api_gateway`)

Responsibilities:

- Provide external `/generate` endpoint.
- Validate request body.
- Forward request to model server’s `/generate`.
- (Optionally) handle caching, rate limiting, auth, logging, DB persistence.

Current version is a simple HTTP proxy; can be extended later.

---

## 7. Frontend (React / TypeScript)

Located in `web-client/`.

Planned components:

- `<ExperimentForm />`
  - Inputs: cell type, treatment, dose, timepoint.
  - On submit: POST to the gateway `/generate`.

- `<Heatmap />` / `<PCAPlot />` (future)
  - Takes `genes` + `expression` from API response.
  - Visualize predicted expression across genes.

For now, a minimal flow is:

1. User fills in form.
2. Request is sent to `/generate`.
3. Raw JSON response is shown in a `<pre>` block.
4. Visualization can be added as a next step.

---

## 8. Repo structure (high level)

- `services/model_server/` — FastAPI + PyTorch CVAE.
- `services/api_gateway/` — Go HTTP proxy for model server.
- `web-client/` — React/TypeScript UI.
- `scripts/` — scripts for preprocessing (`preprocess.py`) and training (future).
- `data/raw/` — raw GEO data (e.g. `GSE102901_series_matrix.txt`).
- `data/processed/` — numpy arrays, CSV metadata.
- `models/` — model weights, encoders, scalers, gene lists.
- `.github/workflows/ci.yml` — CI pipeline (Python + Go tests).

---

## 9. Next steps (for future contributors / tools)

- Implement training code for the CVAE using `data/processed/X_expr.npy` and `X_cond.npy`.
- Wire `inference.py` to load the trained model and artifacts.
- Extend the React UI to visualize expression (heatmaps, summary stats).
- Optionally add:
  - model versioning
  - a simple DB table for experiment logs
  - additional datasets or more complex descriptors
