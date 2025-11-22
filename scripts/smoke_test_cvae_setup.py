"""
Smoke test for CVAE training setup.

Checks:
- X_expr.npy and X_cond.npy load correctly
- shapes are consistent
- one forward+loss computation works with no NaNs/Infs
"""

import numpy as np
import torch

from train_cvae import CVAE, loss_fn  # relies on definitions in train_cvae.py


def main():
    # 1) Load data
    X_expr = np.load("data/processed/X_expr.npy")
    X_cond = np.load("data/processed/X_cond.npy")

    print("Loaded X_expr with shape:", X_expr.shape)
    print("Loaded X_cond with shape:", X_cond.shape)

    assert X_expr.shape[0] == X_cond.shape[0], "Sample count mismatch between X_expr and X_cond"

    expr_dim = X_expr.shape[1]
    cond_dim = X_cond.shape[1]

    # 2) Build a tiny batch (e.g., first 8 samples)
    batch_size = min(8, X_expr.shape[0])
    x_batch = torch.tensor(X_expr[:batch_size], dtype=torch.float32)
    c_batch = torch.tensor(X_cond[:batch_size], dtype=torch.float32)

    # 3) Instantiate model
    model = CVAE(expr_dim=expr_dim, cond_dim=cond_dim, latent_dim=8, hidden_dim=64)
    model.eval()

    # 4) Forward pass + loss
    with torch.no_grad():
        recon, mu, logvar = model(x_batch, c_batch)
        loss = loss_fn(recon, x_batch, mu, logvar)

    print("recon shape:", recon.shape)
    print("mu shape:", mu.shape)
    print("logvar shape:", logvar.shape)
    print("loss:", loss.item())

    # Basic sanity checks
    assert recon.shape == x_batch.shape, "Reconstruction shape mismatch"
    assert mu.shape[0] == batch_size, "Latent batch size mismatch"
    assert torch.isfinite(loss), "Loss is not finite (NaN or Inf)"

    print("✅ Smoke test passed: model, data, and loss function are consistent.")


if __name__ == "__main__":
    main()
