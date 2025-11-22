import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset
import os

X_expr = np.load("data/processed/X_expr.npy")
X_cond = np.load("data/processed/X_cond.npy")

expr_dim = X_expr.shape[1]
cond_dim = X_cond.shape[1]

class CVAE(nn.Module):
    """
    Conditional Variational Autoencoder (CVAE) for gene expression generation.
    
    This model learns to generate gene expression profiles conditioned on
    conditional features (e.g., cell type, treatment conditions). It consists
    of an encoder that maps (expression, condition) pairs to a latent distribution,
    and a decoder that reconstructs expression from latent samples and conditions.
    """
    def __init__(self, expr_dim, cond_dim, latent_dim=32, hidden_dim=256):
        """
        Initialize the CVAE model.
        
        Args:
            expr_dim (int): Dimensionality of the gene expression vector.
            cond_dim (int): Dimensionality of the conditional features vector.
            latent_dim (int, optional): Dimensionality of the latent space. Defaults to 32.
            hidden_dim (int, optional): Dimensionality of hidden layers. Defaults to 256.
        """
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
        """
        Encode expression and condition into latent distribution parameters.
        
        Args:
            x (torch.Tensor): Gene expression tensor of shape (batch_size, expr_dim).
            cond (torch.Tensor): Conditional features tensor of shape (batch_size, cond_dim).
        
        Returns:
            tuple: (mu, logvar) where:
                - mu (torch.Tensor): Mean of latent distribution, shape (batch_size, latent_dim).
                - logvar (torch.Tensor): Log variance of latent distribution, shape (batch_size, latent_dim).
        """
        h = self.encoder(torch.cat([x, cond], dim=1))
        return self.fc_mu(h), self.fc_logvar(h)

    def reparameterize(self, mu, logvar):
        """
        Reparameterization trick to sample from latent distribution.
        
        Samples z ~ N(mu, sigma^2) where sigma^2 = exp(logvar) by computing
        z = mu + eps * sigma, where eps ~ N(0, 1). This allows gradients to
        flow through the sampling operation.
        
        Args:
            mu (torch.Tensor): Mean of latent distribution, shape (batch_size, latent_dim).
            logvar (torch.Tensor): Log variance of latent distribution, shape (batch_size, latent_dim).
        
        Returns:
            torch.Tensor: Sampled latent vectors, shape (batch_size, latent_dim).
        """
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def decode(self, z, cond):
        """
        Decode latent vector and condition into reconstructed expression.
        
        Args:
            z (torch.Tensor): Latent vector tensor of shape (batch_size, latent_dim).
            cond (torch.Tensor): Conditional features tensor of shape (batch_size, cond_dim).
        
        Returns:
            torch.Tensor: Reconstructed gene expression, shape (batch_size, expr_dim).
        """
        return self.decoder(torch.cat([z, cond], dim=1))

    def forward(self, x, cond):
        """
        Forward pass through the CVAE.
        
        Args:
            x (torch.Tensor): Gene expression tensor of shape (batch_size, expr_dim).
            cond (torch.Tensor): Conditional features tensor of shape (batch_size, cond_dim).
        
        Returns:
            tuple: (recon, mu, logvar) where:
                - recon (torch.Tensor): Reconstructed expression, shape (batch_size, expr_dim).
                - mu (torch.Tensor): Latent distribution mean, shape (batch_size, latent_dim).
                - logvar (torch.Tensor): Latent distribution log variance, shape (batch_size, latent_dim).
        """
        mu, logvar = self.encode(x, cond)
        z = self.reparameterize(mu, logvar)
        recon = self.decode(z, cond)
        return recon, mu, logvar


def loss_fn(recon, x, mu, logvar):
    """
    Compute the CVAE loss function.
    
    The loss combines reconstruction error (MSE) and KL divergence regularization.
    The KL term encourages the learned latent distribution to be close to a standard
    normal distribution, promoting smooth latent space and preventing posterior collapse.
    
    Args:
        recon (torch.Tensor): Reconstructed expression, shape (batch_size, expr_dim).
        x (torch.Tensor): Target expression, shape (batch_size, expr_dim).
        mu (torch.Tensor): Latent distribution mean, shape (batch_size, latent_dim).
        logvar (torch.Tensor): Latent distribution log variance, shape (batch_size, latent_dim).
    
    Returns:
        torch.Tensor: Scalar loss value (MSE + KL divergence).
    """
    mse = torch.mean((recon - x) ** 2)
    kld = -0.5 * torch.mean(1 + logvar - mu**2 - torch.exp(logvar))
    return mse + kld


def main():
    """
    Main training function for the CVAE model.
    
    Loads preprocessed gene expression and condition data, creates a DataLoader,
    initializes the model and optimizer, trains for a specified number of epochs,
    and saves the trained model checkpoint.
    """
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
