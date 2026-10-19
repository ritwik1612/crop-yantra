# Paddy — Rice Yield Prediction and Crop Health

Open [the Windows app guide](desktop/README.md) for the offline installer, local
trained-model inference, district map, dark theme and explained predictions.
The previous Vercel deployment has been removed. Paddy's name and rice-plant logo
are confirmed. Installers are distributed through GitHub Releases. No cloud
inference is needed.

models/tabular.py contains the GBDT baseline factory and MLP predictor.
models/temporal.py contains the LSTM and 1D CNN sequence predictor definitions.
The yield studio now selects Contextual Residual MLP or HistGradientBoostingRegressor.
The neural model reuses 28 standard inputs and adds an observed year trend and
train-learned district-season context. Test MAE 0.486, RMSE 0.677 t/ha; the tree
benchmark has MAE 0.532, RMSE 0.672. The feature sets differ; this is not a pure
same-feature architecture comparison. See desktop/README.md for scope and limits.
EfficientNet-B0 performs ten-class rice-condition screening: 85.04% held-out
accuracy and 83.59% macro-F1 on 1,257 test images. MobileNetV3-Small is the trained
comparison model; validation selects EfficientNet, not an ensemble.
Desktop deployment assets
are under prototype/runtime; desktop/ bundles them with the interactive UI.
DAE remains a representation comparison, while sequence models are future work.

Read ../DATASET/training/manifest.json to select predictors and separate YIELD.
Only train.csv fits supervised weights; validation.csv selects settings;
test.csv measures final performance.

The first application uses tabular features. Sequence models require a separate
weather-tensor preparation stage. The LSTM accepts variable-length sequences
with true lengths; the CNN accepts fixed-length, unpadded sequences.
Production and yield must never leak into predictors. Year and district context
are explicit extra inputs ONLY in the contextual neural experiment, with a
training-only vocabulary and scaling. Standard/DAE baselines retain their original
manifest-defined predictors unchanged. A region index is an embedding key, not a
continuous agronomic measurement. New-district generalization is not established.

The trained preprocessing checkpoint is in ../pre-processing/artifacts/.
For deployment, resolve weather and state-season area totals before creating
predictors. Estimate yield in t/ha; production can be estimated by multiplying
predicted yield by user-supplied area.
