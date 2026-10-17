# Image training preparation

Local environment: `OTHER/training_env` (Python 3.11, CPU PyTorch).
The installed libraries include torch, torchvision, scikit-learn, NumPy,
pandas, Pillow, ImageHash, matplotlib, seaborn, Kaggle CLI and pytest.

The official ImageNet EfficientNet-B0 checkpoint is cached under
`APP/models/pretrained/checkpoints`. Its hash and a successful evaluation-only
forward check are recorded in `APP/models/pretrained/backbone_manifest.json`.
This is not a rice-trained classifier.

## Verified local data

The account holder authorized Kaggle CLI OAuth locally. The official ZIP was
downloaded and its full CRC check passed. Credentials remain outside the project;
never copy them into project files or commit third-party images.

| Inventory | Verified value |
| --- | --- |
| Official source archive | 1,093,378,623 bytes (1.09 GB) |
| Labelled source images | 10,407 across 10 classes |
| Selected-class candidates | 4,946 images; 4,120 perceptual groups |
| Prepared subset | 1,600 original photos, 400 per selected class |
| Train / validation / test | 1,120 / 240 / 240 (280 / 60 / 60 per class) |
| Image bytes / total with manifest | 128,435,495 / 129,477,291 bytes |

Selected classes: bacterial leaf blight, blast, brown spot and normal.
No cross-label duplicate-group conflicts or decode exclusions were found among
the selected-class candidates. One representative per perceptual group was
eligible for selection. Grouping is not proof of independent plants or sessions.
The photo-free [inventory](dataset_inventory.json) records source and manifest
hashes. The full manifest stays with the local prepared data.

The preserved source is in `DATASET/images/source/`. To reproduce preparation
into a new output directory, without extracting every competition image:

```powershell
& './OTHER/training_env/Scripts/python.exe' APP/training/images/prepare_data.py --archive 'DATASET/images/source/paddy-disease-classification.zip'
```

The preparer targets up to 400 distinct perceptual groups for each of
bacterial leaf blight, blast, brown spot and normal. It excludes corrupt images,
clusters exact/near duplicates before splitting, removes cross-label group
conflicts, and chooses one image per group. Splits are approximately 70/15/15.
The verified release supplies enough distinct groups for all four 400-image caps.

It writes original image bytes and `manifest.json` to the prepared subset.
No augmentation is applied before splitting. No images are downloaded or rice
models trained by this preparation command. Actual-image integrity checks and
an evaluation-only real-image forward pass have passed. No supervised weights
were updated.

Check the actual prepared image data and a four-output forward pass:

```powershell
& './OTHER/training_env/Scripts/python.exe' APP/training/images/train.py
```

Only after reviewing those checks, explicitly start training:

```powershell
& './OTHER/training_env/Scripts/python.exe' APP/training/images/train.py --train --epochs 15 --head-epochs 5
```

The classifier trains its head first, then the last two backbone blocks. Only
training images receive augmentation. Lowest validation cross-entropy chooses
the checkpoint; test metrics are calculated after selection. Class order,
macro-F1, per-class metrics and confusion matrix are saved with the model.
No app activation, disease-risk forecasting, confidence calibration or unknown-
crop rejection is claimed. Do not adjust the trained yield from disease labels.

Unit checks (generated noise fixtures only, not production crop photos):

```powershell
& './OTHER/training_env/Scripts/python.exe' -m pytest APP/tests/test_image_training.py -q
```

Recorded local CPU environment: `requirements-local-cpu.lock.txt`. This is not a
CUDA/Colab environment lock. No supervised training was performed during setup.

For the already prepared tabular yield data, check without training:

```powershell
& './OTHER/training_env/Scripts/python.exe' APP/training/train.py
```

On Colab use its matched CUDA torch/torchvision installation; do not install the
local CPU wheel there. Install the remaining requirements as needed. Training
must be explicitly started later, after the dataset and splits are verified.
