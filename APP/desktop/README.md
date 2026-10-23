# Paddy for Windows — 0.7.0

Offline rice yield scenarios and rice-photo screening.

## Install

Run releases/Paddy-Setup-0.7.0.exe or download it from
[GitHub Releases](https://github.com/ritwik1612/crop-yantra/releases/tag/v0.7.0).
The green/off-white installer uses the approved rice silhouette, defaults to
Program Files, allows another destination and creates a Windows Search shortcut.
Administrator approval is required; unsigned-installer warnings need user review.
Windows 10/11 x64 and Edge WebView2 are required. No Vercel/cloud inference.

## Active models

- **CNN–LSTM**: two Conv1d layers (11→32→32, kernel 3, GELU, padding masks),
  LSTM hidden size 32, concatenate 11 static inputs, Linear43→64, GELU,
  Dropout0.2 (disabled at inference), Linear64→1, inverse target scaling.
  Validation-selected seed42/epoch9; test MAE .474861 t/ha, RMSE .599986,
  R² .191802. There is no tree fallback or averaging with the MLP.
- **EfficientNet-B0**: ImageNet-initialized, rice-fine-tuned ten-class CNN.
  5,905/1,257/1,257 duplicate-safe train/validation/test photos. Test accuracy
  85.04%, macro-F1 83.59%. Candidate screening, not confirmed diagnosis.

Both primary prediction tasks use neural networks. Standalone LSTM/1D CNN,
Residual MLP, tree and DAE artifacts remain research comparisons. The old tree
MAE .453896 uses full-season covariates, so it is not an architecture-only
comparison against the truncated-weather sequence model. No accuracy superiority
is claimed. Deep learning does not make new districts automatically validated.

## Inputs and limitations

Select a map district, season, temperature and rice/total land areas. Optional
rainfall, humidity, wind and radiation modify a training-only median weather
trajectory. Only the prefix ending 60 days before proxy season end enters the
model. Rainfall is apportioned by prefix/season day count, a scenario assumption.
Blank inputs use reference weather, not current measurements. Missing local
references use neighbouring training templates, preferring the same state.
Donor provenance is visible; the same CNN–LSTM predicts yield. No synthetic yield
label was added to training. Transfer accuracy is not locally established.

Rice hectares scale production, not t/ha; total land validates planted area.
Price affects optional gross value only. Photo screening needs no location;
linked yield context does not change image logits or reduce predicted yield.

Architecture includes connected tensor diagrams and timestep explanations.
After a yield run, expand actual latest-run data for input tensors, convolution
features, LSTM states, joined vector and dense activations. Sensitivities occlude
one channel/group to its training reference; they are not additive, causal or
fixed weights. Export PDF saves a typeset summary and the selected health photo,
not an app screenshot.

## Build and verify

From the project root:

```powershell
.\OTHER\training_env\Scripts\python.exe -m unittest APP.tests.test_sequence_runtime APP.training.test_sequences APP.tests.test_branding
.\OTHER\desktop_env\Scripts\python.exe -m unittest APP.tests.test_reporting
.\OTHER\desktop_env\Scripts\python.exe APP/desktop/main.py --self-test
.\OTHER\desktop_env\Scripts\python.exe APP/desktop/build.py
.\OTHER\paddy_build_0_6_0\dist\Paddy\Paddy.exe --self-test
```

Build uses PyInstaller and Inno Setup. No torch, pandas, raw datasets or virtual
environments are shipped. Neural ONNX parity is within 0.000001 t/ha across
2,642 rows. Old tree/MLP model files are excluded from the new setup. Installers
belong in GitHub Releases, not source Git. Preserve historical run results for
honest comparisons; they must not be relabelled as current metrics.
