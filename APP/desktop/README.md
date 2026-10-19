# Paddy for Windows

Offline neural-network rice-yield estimation, tree benchmark and ten-class rice-condition screening. Created by
**23BAI0037 — R Ritwik** and **23BAI0075 — Joshith G**.

## Install and open

Run `releases/Paddy-Setup-0.3.0.exe`. The green/off-white installer defaults to
`C:\Program Files\Paddy`, shows a destination-folder chooser, and creates the
**Paddy** Start menu shortcut. After installation, search for Paddy in Windows
Search. A desktop shortcut is optional. Uninstall through Windows Installed apps.
Administrator approval is needed to install under Program Files.

## Version 0.3.0 models and architecture

- Yield studio selects **Contextual Residual MLP regressor** or
  **HistGradientBoostingRegressor**. Both reuse the 28 standard predictors.
  The neural network adds an observed crop-year trend and a learned
  district-season offset (30 input fields total). It is not a same-feature
  architecture-only comparison against the original tree benchmark.
- Weather MLP: 28 → 64 → 32 → 1, GELU, dropout 0.5 during training only.
  Regional offsets and the trend are initialized on training labels only, then
  jointly optimized with the weather branch. Validation selects epoch 114.
  No validation/test yield is an input or used to fit transforms/vocabularies.
- Test MAE 0.486, RMSE 0.677 t/ha, R² 0.447. The original MLP had MAE 0.560,
  RMSE 0.733. The original tree benchmark has MAE 0.532, RMSE 0.672; its RMSE
  is still slightly better. Models remain available for honest comparison.
  ONNX parity is checked across all 2,018 rows. Temporal cohort performance is
  not independent farm-level or new-district validation.
- MLP explanations show the actual de-standardization calculation and grouped
  reference-occlusion sensitivities. These sensitivities are not additive,
  causal, SHAP, or a guarantee of agronomic influence.
- Architecture has two accessible, mutually exclusive tabs: Yield Prediction
  and Disease Identification. Only the selected flow is visible.
- **EfficientNet-B0** now screens ten conditions: bacterial leaf blight,
  bacterial leaf streak, bacterial panicle blight, blast, brown spot, dead heart,
  downy mildew, hispa, normal and tungro. These include pest-symptom and normal
  labels, not ten separate diseases. District/season do not enter the classifier.
- Image data: 8,419 duplicate-filtered Paddy Doctor photos, 5,905 training /
  1,257 validation / 1,257 test. EfficientNet was selected over MobileNetV3-Small
  by validation macro-F1 (0.8112 vs 0.7904), not by test performance.
- Image test accuracy **85.04%**, macro-F1 **83.59%**, lowest class recall
  **67.21%** for bacterial leaf blight. MobileNet test accuracy/macro-F1 are
  79.16%/77.82%. The older four-class result is not a directly comparable task.
- All 1,257 test photos reproduce the original checkpoint's predicted class
  after ONNX export; largest logit difference 0.0000515. Exact desktop pixel
  transforms are checked too. Test metrics describe raw classification before
  the app's heuristic quality/score abstention guard.
- Photos come from near Tirunelveli, Tamil Nadu. Performance on independent
  South Indian farms, unknown crops and unknown conditions remains unvalidated.

Windows 10 1809 or newer, x64, with Microsoft Edge WebView2 Runtime and .NET
Framework 4.6.2 or newer. Most current Windows PCs already have these components.
If WebView2 is missing, obtain it from Microsoft's official WebView2 download page.
No Python installation, API key, cloud service or internet connection is required
for predictions. External source-reference links need internet access.

This academic installer is **unsigned**; Windows may display an unknown-publisher
or reputation warning. No security settings are changed by the installer.

## How the EXE works

- A resizable native WebView2 window preserves the HTML/CSS/SVG map and charts.
- Hover, state zoom, district selection, pan, keyboard navigation and theme changes
  remain client-side. Python prediction calls are asynchronous and do not replace
  the interactive map with an image.
- The saved standard preprocessor feeds **MLP** or **HistGradientBoostingRegressor** using
  28 inputs. The exact boosted-tree structure is exported to portable JSON.
- **EfficientNet-B0** runs on CPU using ONNX Runtime. Photo transforms reproduce
  the original evaluation transform, including bicubic resize and centre crop.
- Contrast, lighting and basic blur checks flag poor photos. A 0.65 score gate is
  a conservative heuristic, not calibrated diagnostic confidence or a validated
  unknown-crop detector.
- Images are passed to local Python in memory; they are not uploaded or saved.
- Disease reference cards preserve the season-aware illustrations and flip to
  actual symptom photographs on hover or click/keyboard activation. Photos are
  bundled for offline use, with original authorship and license links.
- Browser settings are stored under the current user's Local AppData/Paddy,
  not in Program Files. Raw training photos and the training environment are not
  included in the application.

## Scope of yield prediction

Select an existing district/year/season record from 2001–2019. Complete historical
weather and district crop-area inputs are retrieved by exact match. The model is
not a live forecast or a validated farm-scale predictor. No nearby-district or
synthetic weather fallback is used for missing records.

The user's hectares multiply the model's yield to estimate production; they do
not replace historical district-level crop area. Yield labels and production
labels never enter the model inputs. An expandable output flow shows actual raw
and transformed features, model version, neural reference sensitivities or additive tree-path contributions.
These contributions are not SHAP values or causal feature effects.

The image task is separate: bacterial leaf blight, blast, brown spot and normal.
Location and season provide reference context, not pixel-classifier inputs.
Image classification does not change predicted yield.

## Build locally

Create an isolated Python 3.11 environment and install `requirements.txt`.
Install Inno Setup 6 separately from its official website. Then, from the project
root, run the environment's Python with `APP/desktop/build.py`.

The build uses the already-exported model assets in `APP/prototype/runtime` and
the committed Paddy icon. It copies an allowlisted static site, bundles Python
with PyInstaller, and compiles the setup with Inno Setup. Intermediate files are
under `OTHER/paddy_build_0_3_0`; final installers are under `APP/desktop/releases`.
Nothing is automatically installed, committed, pushed or published.

`APP/tools/export_deployment.py` reproduces the runtime assets from the original
trained checkpoints and verifies numerical parity. It does not retrain models.
Then run `APP/desktop/export_yield_mlp.py --contextual --source
APP/training/runs/residual_yield_20261019` to export the selected residual network
and its context vocabulary, target/year scaling and measured metrics. Verify
with `python -m unittest APP/tests/test_desktop.py -v` before building.
Finally run `APP/desktop/export_image_model.py` to verify and activate the
validation-selected ten-class image model without overwriting yield metadata.
The original checkpoints and old four-class runtime archive remain preserved.
`APP/tests/test_desktop.py` checks transforms, input guards, real-photo inference,
area arithmetic and explanation reconciliation.

## Distribution

App name: **Paddy**. The elegant rice-plant silhouette is the approved logo.
After testing, source synchronization and a setup-file GitHub Release are
authorized. Executables belong in Releases, not in Git history.

Demo photos are available in the project's top-level **Testing Images** folder,
grouped by true disease class, with a separate known-mistakes section. They are
not packaged in the app, uploaded automatically or added to training data.

Third-party software and dataset provenance remain applicable. Preserve source
attributions and review redistribution conditions before external distribution.
