"""Supervised yield model definitions; fitted checkpoints live in training/runs."""
from sklearn.ensemble import HistGradientBoostingRegressor
from torch import nn

def make_gbdt(seed=42):
    """Baseline; tune hyperparameters on the chronological validation split."""
    return HistGradientBoostingRegressor(max_iter=200, max_leaf_nodes=15,
                                        learning_rate=0.05, random_state=seed,
                                        early_stopping=False)

class YieldMLP(nn.Module):
    """Latent/context predictors -> 64 -> 32 -> one yield estimate."""
    def __init__(self, input_dim):
        super().__init__()
        self.network=nn.Sequential(nn.Linear(input_dim,64),nn.GELU(),nn.Dropout(0.2),
                                   nn.Linear(64,32),nn.GELU(),nn.Linear(32,1))
    def forward(self, values):
        return self.network(values).squeeze(-1)
