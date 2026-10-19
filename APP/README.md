# Paddy — Rice Yield Prediction and Crop Health

Open [the Windows app guide](desktop/README.md) for the offline installer, local
trained-model inference, district map, dark theme and explained predictions.
The previous Vercel deployment has been removed. Paddy's name and rice-plant logo
are confirmed. Installers are distributed through GitHub Releases. No cloud
inference is needed.

models/tabular.py contains the GBDT baseline factory and MLP predictor.
models/temporal.py contains the LSTM and 1D CNN sequence predictor definitions.
The yield studio automatically uses the validation-selected HistGradientBoostingRegressor;
there is no model selector. It uses 30 standard inputs (21 numerical plus 9
category indicators). Recent held-out MAE is 0.454 and RMSE 0.571 t/ha.
The Contextual Residual MLP is a separate research comparison with a learned
district-season context and no year trend in the selected configuration.
Its recent test MAE is 0.605 and RMSE 0.819 t/ha, weaker than the tree.
See desktop/README.md for scope, split counts and limits.
EfficientNet-B0 performs ten-class rice-condition screening: 85.04% held-out
accuracy and 83.59% macro-F1 on 1,257 test images. MobileNetV3-Small is the trained
comparison model; validation selects EfficientNet, not an ensemble.
Desktop deployment assets
are under prototype/runtime; desktop/ bundles them with the interactive UI.
DAE remains a representation comparison, while sequence models are future work.

Read ../DATASET/training/recent/manifest.json for the active predictors and separate YIELD.
Only train.csv fits supervised weights; validation.csv selects settings;
test.csv measures final performance.

The first application uses tabular features. Sequence models require a separate
weather-tensor preparation stage. The LSTM accepts variable-length sequences
with true lengths; the CNN accepts fixed-length, unpadded sequences.
Production and yield must never leak into predictors. District context
is an explicit extra input ONLY in the contextual neural experiment, with a
training-only vocabulary. The selected network disables its year term.
Standard/DAE baselines retain their original
manifest-defined predictors unchanged. A region index is an embedding key, not a
continuous agronomic measurement. New-district generalization is not established.

The trained preprocessing checkpoint is in ../pre-processing/artifacts/.
For deployment, resolve weather and state-season area totals before creating
predictors. Estimate yield in t/ha; production can be estimated by multiplying
predicted yield by user-supplied area.
