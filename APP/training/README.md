# Training preparation (no yield training performed yet)

Start with the [shared runbook](START_TRAINING.md) for both yield and image
training. `python APP/training/run.py` checks both without fitting and writes
`APP/training/readiness.json`. Training always requires an explicit `--train`.
The optional [Colab notebook](Train_Both.ipynb) defaults to no training as well.

From the repository root, check the six exported partitions without fitting:

```bash
python APP/training/train.py
```

Checks row counts, chronological boundaries, finite predictors/labels, duplicate
keys, split overlap, exact representation alignment and predictor leakage.
Reports hashes and missing training libraries. Check-only does not need PyTorch
or scikit-learn, but does need pandas and NumPy.

When the team is ready, install the recorded preprocessing environment from
`pre-processing/requirements.txt` in an isolated environment or Colab. Trusted
saved artifacts are version-dependent. Do not silently substitute incompatible
scikit-learn versions when loading pickled transforms.

**Do not run the following until training is intended:**

```bash
python APP/training/train.py --train --epochs 250 --seed 42
```

Runs standard/DAE × MLP/HistGradientBoostingRegressor. Training uses only each
representation's train.csv and manifest predictors. MLP target normalization
uses training statistics only. Validation chooses best MLP epoch and one of
three tree configurations. MAE/RMSE/R², test residuals and state/season breakdowns
are exported only after selection. A comparison chooses the best experiment by
validation RMSE, never test scores. For defensible neural results, repeat seeds
and report variability. The runner does not automate multi-seed aggregation or
reconstruction-score ablation yet.

Each run creates a **new** `APP/training/runs/<timestamp>/` directory containing
four model bundles, metrics, histories, test predictions and comparison.json.
Existing output directories are not overwritten. Bundles retain schema, source
hashes and preprocessing artifact hashes. No model is automatically activated
in the webpage. The test set should not guide further tuning after evaluation.

Exact input files:

- DATASET/training/standard/train.csv, validation.csv, test.csv
- DATASET/training/autoencoder/train.csv, validation.csv, test.csv
- DATASET/training/manifest.json (predictor/target contract)

Only the two train.csv files fit supervised weights. Validation and test are
held out. Raw downloads and rice_master.csv are not fed directly into predictors.
The mean-yield training baseline should be added to the final comparison.
LSTM/1D CNN need sequence preparation and are outside this runner.

## Future inference

`APP/inference/preprocess.py` accepts complete 21-feature rows plus STATE/SEASON
and reuses saved preprocessing (no fitting). `APP/inference/predict.py` accepts
those rows plus an explicitly selected trained bundle. It refuses absent weights
or incompatible hashes and never silently substitutes a demo result.

```bash
python APP/inference/predict.py --features complete_features.json --bundle APP/training/runs/RUN/autoencoder_mlp
```

The isolated desktop environment now includes torch and scikit-learn, and the
tabular check-only command passes. Supervised yield fitting and trained-bundle
inference have not been run. Verify saved preprocessing package compatibility
before serving raw-row inference; installed libraries alone do not validate it.
The browser beta remains browser-local. A weather/area-context service and
validated browser-to-backend connection must be built before live predictions.
No feature-attribution, uncertainty, disease detection or early forecast is claimed.

## Auxiliary rice-image classifier

See [image preparation and explicit training commands](images/README.md).
This separate EfficientNet-B0 classifier uses rice photographs, not tabular yield
rows. Its check-only entry point never starts supervised training.
