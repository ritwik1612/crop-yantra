# Training file navigation

## Current models (0.4.0)

Use `recent/standard/train.csv` (1,984 rows, 2001–2020),
`recent/standard/validation.csv` (321 rows, 2021–2022), and
`recent/standard/test.csv` (337 rows, 2023–2024).
The contract is `recent/manifest.json`. These contain 30 standard predictors
(21 numerical + 9 one-hot indicators) and retained metadata/target fields.
Contextual MLP also uses a training-learned district-season embedding; its
selected no-year-trend graph has a reserved constant-zero year slot.
Its fitted preprocessor/checkpoint is under
`APP/training/runs/recent_yield_20261019`. Never merge partitions for fitting.

## Preserved old baseline — not active training inputs

| Representation | Fit weights | Select settings | Final evaluation |
| --- | --- | --- | --- |
| Conventional | standard/train.csv | standard/validation.csv | standard/test.csv |
| DAE | autoencoder/train.csv | autoencoder/validation.csv | autoencoder/test.csv |

Rows: 1,485 train; 245 validation; 288 test.
Conventional: 28 predictors. DAE: 16 predictors, including optional
AE_RECONSTRUCTION_MSE. Both representations preserve YIELD and selected
metadata in addition to predictors.

The deployed Contextual Residual MLP reads the **standard** partitions. It
adds the retained observed crop year and district/season identity through
training-fitted year scaling and a learned embedding; these are explicit model
inputs, not new invented data rows. DAE files remain the comparison experiment.

Use manifest.json: select predictor_columns, and select YIELD separately as
the label. Never include every CSV column as an input feature.

Future sequence models use separately prepared weather tensors; these CSVs
are the current tabular training representations.
