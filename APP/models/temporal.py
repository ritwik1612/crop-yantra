"""Weather sequence regressors; training status is recorded in each run manifest."""
import torch
from torch import nn
from torch.nn.utils.rnn import pack_padded_sequence

class YieldLSTM(nn.Module):
    """Padded weather [batch,time,10], true lengths, static/context features."""
    def __init__(self, static_dim, weather_dim=10, hidden_dim=64):
        super().__init__()
        self.lstm=nn.LSTM(weather_dim,hidden_dim,num_layers=2,batch_first=True,dropout=0.2)
        self.head=nn.Sequential(nn.Linear(hidden_dim+static_dim,64),nn.GELU(),
                                nn.Dropout(0.2),nn.Linear(64,1))
    def forward(self, weather, lengths, static):
        packed=pack_padded_sequence(weather,lengths.cpu(),batch_first=True,enforce_sorted=False)
        _,(hidden,_)=self.lstm(packed)
        return self.head(torch.cat([hidden[-1],static],dim=1)).squeeze(-1)

class YieldCNN(nn.Module):
    """Fixed-length weather [batch,time,10] plus static/context features."""
    def __init__(self, static_dim, weather_dim=10):
        super().__init__()
        self.features=nn.Sequential(nn.Conv1d(weather_dim,32,3,padding=1),nn.GELU(),
                                    nn.Conv1d(32,64,3,padding=1),nn.GELU(),
                                    nn.AdaptiveAvgPool1d(1))
        self.head=nn.Sequential(nn.Linear(64+static_dim,64),nn.GELU(),
                                nn.Dropout(0.2),nn.Linear(64,1))
    def forward(self, weather, static):
        encoded=self.features(weather.transpose(1,2)).squeeze(-1)
        return self.head(torch.cat([encoded,static],dim=1)).squeeze(-1)


class MaskedYieldCNN(nn.Module):
    """Length-aware temporal convolutions plus static location/season context."""
    def __init__(self, static_dim, weather_dim=10, hidden_dim=64):
        super().__init__()
        self.conv1 = nn.Conv1d(weather_dim, hidden_dim, 3, padding=1)
        self.conv2 = nn.Conv1d(hidden_dim, hidden_dim, 3, padding=1)
        self.head = nn.Sequential(nn.Linear(hidden_dim + static_dim, 64), nn.GELU(),
                                  nn.Dropout(.2), nn.Linear(64, 1))

    def encode(self, weather, lengths):
        mask = (torch.arange(weather.shape[1], device=weather.device)[None, :] < lengths[:, None])[:, None, :]
        x = weather.transpose(1, 2) * mask
        x = torch.nn.functional.gelu(self.conv1(x)) * mask
        x = torch.nn.functional.gelu(self.conv2(x)) * mask
        return x, mask

    def forward(self, weather, lengths, static):
        x, mask = self.encode(weather, lengths)
        pooled = x.sum(dim=2) / lengths[:, None].clamp_min(1)
        return self.head(torch.cat([pooled, static], dim=1)).squeeze(-1)


class YieldCNNLSTM(MaskedYieldCNN):
    """Convolutions learn local weather patterns; LSTM learns their ordering."""
    def __init__(self, static_dim, weather_dim=10, hidden_dim=64):
        super().__init__(static_dim, weather_dim, hidden_dim)
        self.lstm = nn.LSTM(hidden_dim, hidden_dim, batch_first=True)

    def forward(self, weather, lengths, static):
        x, _ = self.encode(weather, lengths)
        packed = pack_padded_sequence(x.transpose(1, 2), lengths.cpu(), batch_first=True, enforce_sorted=False)
        _, (hidden, _) = self.lstm(packed)
        return self.head(torch.cat([hidden[-1], static], dim=1)).squeeze(-1)
