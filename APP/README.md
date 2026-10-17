# Paddy — Rice Yield Prediction and Crop Health

Open [the Windows app guide](desktop/README.md) for the offline installer, local
trained-model inference, district map, dark theme and explained predictions.
The previous Vercel deployment has been removed. Paddy's name and rice-plant logo
are confirmed. Installers are distributed through GitHub Releases. No cloud
inference is needed.

models/tabular.py contains the GBDT baseline factory and MLP predictor.
models/temporal.py contains the LSTM and 1D CNN sequence predictor definitions.
The selected trained yield model is standard HistGradientBoostingRegressor.
EfficientNet-B0 performs four-class rice screening. Desktop deployment assets
are under prototype/runtime; desktop/ bundles them with the interactive UI.
MLP and DAE remain comparison experiments, while sequence models are future work.

Read ../DATASET/training/manifest.json to select predictors and separate YIELD.
Only train.csv fits supervised weights; validation.csv selects settings;
test.csv measures final performance.

The first application uses tabular features. Sequence models require a separate
weather-tensor preparation stage. The LSTM accepts variable-length sequences
with true lengths; the CNN accepts fixed-length, unpadded sequences.
Crop year, region IDs and production must not accidentally become predictors.

The trained preprocessing checkpoint is in ../pre-processing/artifacts/.
For deployment, resolve weather and state-season area totals before creating
predictors. Estimate yield in t/ha; production can be estimated by multiplying
predicted yield by user-supplied area.
