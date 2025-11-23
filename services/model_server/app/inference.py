import os
import json
from typing import Dict, Any

import numpy as np
import pandas as pd
import torch
from torch import nn
import joblib

# Paths relative to app/ directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODELS_DIR = os.path.join(BASE_DIR, "..", "..", "..", "models")
PROCESSED_DIR = os.path.join(BASE_DIR, "..", "..", "..", "data", "processed")

GENES_PATH = os.path.join(MODELS_DIR, "genes_gse60424.json")
DESIGN_ENCODER_PATH = os.path.join(MODELS_DIR, "design_encoder_gse60424.pkl")
EXPR_SCALER_PATH = os.path.join(MODELS_DIR, "expr_scaler_gse60424.pkl")
META_PATH = os.path.join(PROCESSED_DIR, "meta.csv")
MODEL_WEIGHTS_PATH = os.path.join(MODELS_DIR, "cvae_gse60424.pt")

MODEL_VERSION = "cvae_gse60424_v1"


class CVAE(nn.Module):
    def __init__(self, expr_dim: int, cond_dim: int, latent_dim: int = 32, hidden_dim: int = 256):
        super().__init__()
        self.encoder = nn.Sequential(
            nn.Linear(expr_dim + cond_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim + cond_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, expr_dim),
        )

    def encode(self, x, cond):
        h = self.encoder(torch.cat([x, cond], dim=1))
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z, cond):
        return self.decoder(torch.cat([z, cond], dim=1))

    def forward(self, x, cond):
        mu, logvar = self.encode(x, cond)
        z = self.reparameterize(mu, logvar)
        recon = self.decode(z, cond)
        return recon, mu, logvar


# Global objects initialized once
_device = torch.device("cpu")

_genes = None
_design_encoder = None
_expr_scaler = None
_meta_df = None
_cond_fields = None
_model = None


def _load_artifacts():
    global _genes, _design_encoder, _expr_scaler, _meta_df, _cond_fields, _model

    # Load genes (list of selected gene IDs)
    with open(GENES_PATH, "r") as f:
        _genes = json.load(f)

    # Load encoders / scalers
    _design_encoder = joblib.load(DESIGN_ENCODER_PATH)
    _expr_scaler = joblib.load(EXPR_SCALER_PATH)

    # Load metadata to know conditioning fields and their order
    _meta_df = pd.read_csv(META_PATH, index_col=0)
    _cond_fields = list(_meta_df.columns)  # we used all metadata columns when fitting

    # Infer shapes
    expr_dim = len(_genes)
    dummy_row = _meta_df[_cond_fields].astype(str).iloc[[0]]
    cond_example = _design_encoder.transform(dummy_row.values.astype(str))
    cond_dim = cond_example.shape[1]

    # Initialize model and load weights
    _model = CVAE(expr_dim=expr_dim, cond_dim=cond_dim, latent_dim=32, hidden_dim=256)
    state_dict = torch.load(MODEL_WEIGHTS_PATH, map_location=_device)
    _model.load_state_dict(state_dict)
    _model.to(_device)
    _model.eval()


def _ensure_loaded():
    if any(obj is None for obj in [_genes, _design_encoder, _expr_scaler, _meta_df, _cond_fields, _model]):
        _load_artifacts()


def _build_cond_row(descriptor: Dict[str, Any]) -> np.ndarray:
    """
    Build a 1-row conditioning matrix from a free-form descriptor.

    Strategy:
    - Start from the modal (most common) values in meta_df as defaults.
    - Override with any keys provided in descriptor (matching column names).
    - Convert to DataFrame with a single row.
    - Apply the same OneHotEncoder used in preprocessing.
    """
    # default values: mode for each column
    defaults = _meta_df.mode().iloc[0].to_dict()

    # override with user-provided keys (case-insensitive match)
    normalized_cols = {c.lower(): c for c in _cond_fields}
    for key, value in descriptor.items():
        k_norm = str(key).lower()
        if k_norm in normalized_cols:
            col = normalized_cols[k_norm]
            defaults[col] = value

    row_df = pd.DataFrame([defaults])[ _cond_fields ].astype(str)

    X_cond = _design_encoder.transform(row_df.values.astype(str)).astype("float32")
    return X_cond


def generate_expression(descriptor: Dict[str, Any], seed: int | None = None):
    """
    Main entry point used by FastAPI:
    - descriptor: dict from request body["descriptor"]
    - seed: optional int for reproducibility (if provided)
    """
    _ensure_loaded()

    # Build conditioning vector
    X_cond = _build_cond_row(descriptor)
    cond_t = torch.tensor(X_cond, dtype=torch.float32, device=_device)

    # Sample latent z
    expr_dim = len(_genes)

    if seed is not None:
        torch.manual_seed(seed)

    latent_dim = 32
    z = torch.randn((1, latent_dim), device=_device)

    with torch.no_grad():
        recon_scaled = _model.decode(z, cond_t)  # in standardized (scaled) space

    # Convert back to numpy
    recon_scaled_np = recon_scaled.cpu().numpy()

    # Inverse transform scaling to get back to log1p(normalized) space
    expr_log = _expr_scaler.inverse_transform(recon_scaled_np)

    # Optionally: we could exponentiate (np.expm1) to get back to "approx counts".
    expr_values = expr_log[0].tolist()

    return _genes, expr_values, MODEL_VERSION
