"""Temporal, known-district yield network. Not a new-district generalization model."""
import torch
from torch import nn
from APP.models.tabular import YieldMLP


class ContextualYield(nn.Module):
    def __init__(self, district_count, dropout=.35):
        super().__init__()
        self.weather=YieldMLP(28)
        self.weather.network[2].p=dropout
        self.district=nn.Embedding(district_count+1,1,padding_idx=0)
        self.trend=nn.Linear(1,1,bias=False)
        nn.init.zeros_(self.district.weight)
        nn.init.zeros_(self.trend.weight)

    def forward(self, inputs):
        # Index zero is an explicit unknown-district reference. Year uses
        # train-only centering/scaling, not a future yield statistic.
        return self.weather(inputs[:,:28])+self.district(inputs[:,29].long()).squeeze(-1)+self.trend(inputs[:,28:29]).squeeze(-1)
