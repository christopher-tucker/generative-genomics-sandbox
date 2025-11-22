import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import joblib
import json
import os

X_expr = np.load("data/processed/X_expr.npy")
X_cond = np.load("data/processed/X_cond.npy")

expr_dim = X_expr.shape[1]
cond_dim = X_cond.shape[1]

class CVAE(nn.Module):
    def __init__(self, expr_dim, cond_dim, latent_dim=32, hidden_dim=256):
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


def loss_fn(recon, x, mu, logvar):
    mse = torch.mean((recon - x) ** 2)
    kld = -0.5 * torch.mean(1 + logvar - mu**2 - torch.exp(logvar))
    return mse + kld


def main():
    X_expr_t = torch.tensor(X_expr, dtype=torch.float32)
    X_cond_t = torch.tensor(X_cond, dtype=torch.float32)

    ds = TensorDataset(X_expr_t, X_cond_t)
    dl = DataLoader(ds, batch_size=16, shuffle=True)

    model = CVAE(expr_dim, cond_dim)
    opt = torch.optim.Adam(model.parameters(), lr=1e-3)

    epochs = 40
    for epoch in range(epochs):
        total_loss = 0
        for x, cond in dl:
            recon, mu, logvar = model(x, cond)
            loss = loss_fn(recon, x, mu, logvar)
            opt.zero_grad()
            loss.backward()
            opt.step()
            total_loss += loss.item()

        avg = total_loss / len(dl)
        print(f"Epoch {epoch+1}/{epochs}  Loss={avg:.4f}")

    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), "models/cvae_gse60424.pt")
    print("Saved model to models/cvae_gse60424.pt")


if __name__ == "__main__":
    main()
