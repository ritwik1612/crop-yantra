# Crop Yantra — training runbook

> Historical runbook. Training has since completed. Use SEQUENCE_TRAINING.md
> for the active CNN–LSTM route (1,984/321/337 chronological rows) and
> images/README.md for the ten-class image pipeline. The old preparation-only
> status and four-class counts below describe the original experiment only.

Preparation is complete locally; no supervised yield or rice-image training has
been started. The DAE preprocessing model was fitted previously and is reused,
not retrained by these commands. No trained predictor is activated in the app.

## Models and exact inputs

| Task | Models | Training input | Held-out data |
| --- | --- | --- | --- |
| Rice yield | MLP and HistGradientBoostingRegressor, each with standard and DAE features: four experiments | The two `DATASET/training/{standard,autoencoder}/train.csv` files, 1,485 aligned observations each | 245 validation and 288 test observations per representation |
| Rice health | ImageNet-pretrained EfficientNet-B0, four-class replacement head | 1,120 photos identified as `train` in the prepared image manifest | 240 validation and 240 test photos |

The two yield representations describe the same 2,018 observations; they are
not 4,036 independent examples. Standard has 28 predictors; DAE has 16.
The label is YIELD in tonnes/hectare. Chronological years are 2001–2015,
2016–2017 and 2018–2019. The neighbour-augmented table is not silently used.

Images have 400 examples per class: bacterial leaf blight, blast, brown spot and
normal; each class contributes 280/60/60 to the three splits. The 129.48 MB local
subset retains original photos and a provenance manifest. Raw archives, app
illustrations and unlabelled competition test images are not training inputs.

## Local Windows commands

Run from the project root using the installed Python 3.11 environment. No
activation or additional installation is required on this PC.

```powershell
# Safe: verifies both pipelines and saves APP/training/readiness.json; no fitting.
& './OTHER/training_env/Scripts/python.exe' APP/training/run.py

# Run only when supervised training is intended:
& './OTHER/training_env/Scripts/python.exe' APP/training/run.py --task yield --train
& './OTHER/training_env/Scripts/python.exe' APP/training/run.py --task images --train

# Alternatively run yield, then images, stopping if either fails:
& './OTHER/training_env/Scripts/python.exe' APP/training/run.py --task both --train
```

Check a single task with `--task yield` or `--task images`, omitting `--train`.
Configurable defaults: `--yield-epochs 250`, `--image-epochs 15`,
`--image-head-epochs 5`, `--image-batch-size 32`, `--seed 42`.
The image first phase trains the head; the second fine-tunes the final two
backbone blocks. Both runners use validation for model/checkpoint selection.
The local environment is CPU-only. Image training uses CUDA automatically if a
compatible GPU runtime is supplied. Tabular training deliberately uses CPU.

## Verification performed before training

The shared preflight checks chronological splits, finite values, leakage/overlap,
alignment, all saved preprocessing outputs against the master table, MLP forward
shapes, tree construction, every selected photo's hash/decoding, duplicate groups,
class mappings, image transforms, pretrained checkpoint integrity and a real-image
forward pass. It performs no optimizer steps and fits no estimator.
The full source ZIP CRC was verified at acquisition. That acquisition record is
not a substitute for the current per-photo checks.

`APP/training/readiness.json` records versions, hashes and current readiness.
Unit tests are in `APP/tests`; they do not establish predictive accuracy.
Only trusted local preprocessing pickle/checkpoints are loaded; never replace
them with arbitrary downloaded pickle files. The common dependency list is
`APP/training/requirements.txt`, with the exact local CPU lock under `images/`.

## Optional Colab GPU transfer

Open `Train_Both.ipynb` in Colab and select a GPU runtime before installing.
Upload the locally prepared `crop_yantra_training.zip` from
`OTHER/training_transfer`. The notebook verifies transfer hashes, installs the
common dependencies without replacing Colab's CUDA torch/torchvision, then runs
preflight. Both training switches default to False. You must explicitly enable
them to train. Colab execution/GPU availability has not been verified from this PC.

The transfer ZIP contains only allowlisted training code, fitted preprocessing,
master/splits, the 1,600 selected photos and official backbone weights. It excludes
Kaggle credentials, virtual environments, raw 1.09 GB archive, app assets, Git
metadata and existing results. Keep it private and follow competition terms;
do not commit the ZIP or third-party photos to public GitHub.
To rebuild without overwriting an existing ZIP:

```powershell
& './OTHER/training_env/Scripts/python.exe' APP/training/package.py --output OTHER/training_transfer/crop_yantra_training_v2.zip
```

## Outputs after an explicitly started run

New directories under `APP/training/runs/` preserve existing results. Yield runs
save four model bundles, histories, held-out predictions, state/season metrics,
MAE/RMSE/R², a training-mean baseline and a validation-ranked comparison.
Image runs save model weights, class order, history, selected epoch, test loss,
accuracy, macro-F1, per-class metrics and a confusion matrix. Colab results must
be downloaded before its temporary runtime is lost.

Test labels must not guide further tuning. Run multiple seeds before making a
robust performance claim. Accuracy is unknown until evaluation; district-scale
yield data does not validate farm-scale forecasts. Rice-photo origin in Tamil
Nadu does not establish performance in every district or season. The two tasks
have no paired labels: do not automatically lower predicted yield from a photo
diagnosis. Confidence calibration, unknown-crop rejection, web inference and
production deployment remain later validation/integration work.
