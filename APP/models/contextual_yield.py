"""Temporal, known-district yield network. Not a new-district generalization model."""
import torch
from torch import nn
from APP.models.tabular import YieldMLP


class ContextualYield(nn.Module):
    def __init__(self, district_count, dropout=.35, input_count=28):
        super().__init__()
        self.input_count=input_count
        self.weather=YieldMLP(input_count)
        self.weather.network[2].p=dropout
        self.district=nn.Embedding(district_count+1,1,padding_idx=0)
        self.trend=nn.Linear(1,1,bias=False)
        nn.init.zeros_(self.district.weight)
        nn.init.zeros_(self.trend.weight)

    def forward(self, inputs):
        # Index zero is an explicit unknown-district reference. Year uses
        # train-only centering/scaling, not a future yield statistic.
        n=self.input_count
        return self.weather(inputs[:,:n])+self.district(inputs[:,n+1].long()).squeeze(-1)+self.trend(inputs[:,n:n+1]).squeeze(-1)
