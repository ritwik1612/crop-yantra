# Small rice-photo component — Crop Yantra

## Selection and regional fit

Use a **curated subset of Paddy Doctor**, not its full collection. The authors
report field collection near Tirunelveli, Tamil Nadu, with agricultural-officer
annotation: https://paddydoc.github.io/dataset/ . This directly supports South
Indian **rice**, not every South Indian crop and not validated coverage of all
districts, varieties, cameras or seasons.

Source release: https://www.kaggle.com/competitions/paddy-disease-classification/data .
The competition release and the broader research collection are different
versions; record the exact release and filenames used. Read and comply with
competition access/use rules before acquisition or redistribution. Do not
upload third-party images to our public GitHub without permission.

Target **up to 1,600 unique RGB images**, up to 400 each of normal, blast,
brown_spot and bacterial_leaf_blight. These are selection targets, not a
downloaded or verified inventory. Use fewer if independent originals are
insufficient after duplicate removal. Exclude infrared, pests and other classes
from this first auxiliary classifier. Unsupported diseases remain a limitation.

The full competition download is roughly 1.09 GB; choosing a subset does not
make that archive smaller. Prefer selected-file acquisition if supported by the
authorized source; otherwise disclose the full temporary download first. Target
a compact 224-pixel JPEG working set below 200 MB, **an unmeasured storage
budget**, not a verified source-download size. Keep source provenance and exact
byte counts in the acquisition manifest. No image dataset is downloaded yet.

## Models and training

Use **ImageNet-pretrained EfficientNet-B0**, replace its classification head with
four outputs and fine-tune on the selected rice images. ImageNet weights are
generic visual features, not a ready-made rice diagnosis model. No image weights
are currently imported and no image training has started.

Official backbone: https://docs.pytorch.org/vision/stable/models/generated/torchvision.models.efficientnet_b0.html .
Use the checkpoint's documented normalization and evaluation transforms.

1. Validate labels, decoding and RGB format; remove exact/near duplicates.
2. Split original-image groups before augmentation, approximately 70/15/15,
   stratified where feasible. Keep the same plant/capture session in one split
   when metadata permits. If group metadata is unavailable, report that limit.
3. Resize/crop to 224 pixels and normalize. Apply modest augmentation to the
   training split only; retain symptoms and natural colours.
4. Train the new head for 3–5 epochs, then fine-tune final blocks for 5–10 epochs
   with a smaller learning rate and validation-based early stopping. Batch 32
   is a starting point, not a hardware guarantee.
5. Report held-out macro-F1, per-class recall and confusion matrix. Calibrate
   probabilities/abstention on validation only. A softmax score alone does not
   reliably reject unknown crops or unsupported diseases; separately test those
   negatives and permit “cannot identify”.
6. Independently test expert-labelled South Indian field photos, ideally across
   the four project states. Regional origin alone does not prove generalisation.

Planning estimate for this small subset: **10–30 minutes on a Colab T4** for one
short run, excluding acquisition/setup; CPU may take **1–3 hours**. These are
not measurements. Benchmark one epoch before quoting a firm time or accuracy.

## Relationship to the main project

The Denoising Autoencoder (DAE) represents tabular numerical inputs. The MLP
regressor and HistGradientBoostingRegressor are proposed yield predictors.
EfficientNet-B0 is a separate image classifier; it does not replace them.

Yield inputs (district, season, year and area) accompany the photo as context
for advisory text. Existing yield rows are not paired with image labels, so do
not claim trained image/weather fusion or change predicted yield from a disease
label without paired impact data. Never infer disease from low predicted yield.

Current beta: illustrative leaf images, local photo preview and metadata-only
request export. No diagnosis, confidence, outbreak forecast or pesticide advice.
Photos are not transmitted. After training, connect a versioned inference
service; then package the validated app and licensed weights for Windows and
publish an installer/EXE in GitHub Releases. No EXE exists yet.
