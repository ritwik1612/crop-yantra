# Deep-learning yield experiments

The runner never changes the app. LSTM, length-aware 1D CNN and CNN–LSTM have
now completed training with seeds 42 and 73. Validation selected CNN–LSTM seed
42, epoch 9; held-out MAE .474861, RMSE .599986 t/ha, R² .191802.
The separately tested version 0.7.0 export integrates that frozen checkpoint.

## Inputs and target

- Real NASA daily weather: maximum/minimum/average temperature, vapour pressure,
  wind, precipitation, land evaporation, solar radiation, humidity and pressure.
- Consecutive ten-day bins: means for atmospheric variables; totals for rain,
  evaporation and radiation; an additional bin-day-count channel.
- Static branch: two coordinates, four state indicators, five season indicators.
- Target: measured district-season production / harvested crop area, tonnes/ha.
- Excluded: production, target-derived columns, end-season district crop area,
  synthetic neighbour labels, arbitrary ordered aggregate columns.

Only the first part of a season is supplied: default cutoff is 60 days before
the proxy calendar season end. This is not 60 days before an observed harvest.
Rabi/Winter cross years, and Summer belongs to the following calendar year.
No future weather enters inputs. Full-season weather is used only to audit
source joins against the merged dataset, not as prediction features.

## Evaluation

Train <=2020; validation 2021–2022; held-out test 2023–2024. Every original row
must have complete weather and pass seasonal aggregate reconciliation, otherwise
preparation aborts. Train-only scaling excludes padded timesteps. Padding is
masked in convolutions and packed in recurrent networks. Median imputation is
not used to silently fill missing daily weather.

Each architecture is trained with AdamW, gradient clipping, at most 150 epochs,
batch size 64, early stopping after 25 unimproved validation epochs. Epochs,
seeds and final architecture are selected by validation RMSE only. Optional test
evaluation runs only on the frozen overall validation winner. Do not tune further
using its test score. Full-season app model metrics are not directly comparable
to these truncated-weather forecasts. A training-mean baseline is recorded.

Run from the project root with the training environment's Python:

```powershell
.\OTHER\training_env\Scripts\python.exe -m unittest APP.training.test_sequences
.\OTHER\training_env\Scripts\python.exe APP/training/train_sequences.py --run-dir APP/training/runs/sequences_NEW_RUN --train --evaluate-test
```

Prepared tensors, record keys and train-fit scaling parameters are saved under
DATASET/training/sequences_lead60. Use a fresh data directory when changing the
lead time. A run directory cannot be overwritten. Source hashes are recorded.
Run histories/checkpoints stay local, not in Git. CPU execution uses four threads.

## Application policy

EfficientNet-B0 remains the image classifier. CNN–LSTM is the version 0.7.0 yield
route. MLP and trees are archived comparisons, not fallback inference. Export
uses ONNX, parity-verified on all 2,642 rows. The app constructs explicit what-if
weather sequences from training-only median templates and neighbour-weather
transfer; these scenarios are not validated as live forecasts. No accuracy gain
is assumed. Unobserved soil, fertilizer or irrigation effects cannot be claimed.
