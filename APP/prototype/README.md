# Paddy — Rice Yield & Crop Health

## Paddy 0.5.0 — 20 October 2026

The crop-health scene is real Three.js geometry, with a local renderer and
original procedural rice model, textured opaque leaf surfaces, varied shapes,
branched panicles and 672 individual grains. Camera orbit, wind response and
leaf-facing symptom inspection are model-space interactions, not image warps.
Camera/photo controls sit outside the specimen viewport. The JSON model snapshot
and surface-material provenance are documented in assets/RICE_MODEL.md.

Yield, results, method and architecture share the black-only workspace stylesheet.
Architecture diagrams are selectable and task-exclusive. Actual output audits
offer four step-by-step stages or an all-steps view; numerical model inputs,
transformations, logits and calculations remain engine-owned. Yield explanations
include all model-feature contributions, signed feature groups and a checked
baseline reconciliation, not causal percentages. Area and price scaling are
separate from per-hectare yield attribution.

Design influence: Corn Revolution (specimen inspection), Igloo (object/camera
composition), Lusion and Active Theory (dark spatial presentation), Synchronized
and Obys Format (type/grid hierarchy). The other supplied references informed
interaction exploration. No third-party site artwork or 3D assets were copied.
All ten Real photo views use bundled, attributed photographs. Seven previously
local-only competition examples have been replaced by labelled panels from a
CC BY publication. See assets/PHOTO_CREDITS.md. The build checks all ten references
inside the packaged site before compiling the installer.

## Run the real local preview

From the project root in PowerShell:

```powershell
& OTHER/desktop_env/Scripts/python.exe APP/desktop/preview.py
```

Open http://127.0.0.1:8765/. This loopback server uses the actual offline engine.
Opening index.html without the desktop bridge is a legacy interface preview,
not trained inference; do not use that mode for an evaluation demonstration.

## Current interface

- Map-only district selection: hover, state zoom, district selection, pan/zoom
  and keyboard navigation. GADM 4.1 provides 103 source-vintage districts, not
  a current administrative registry.
- Enter season, total land, rice-planted area and average seasonal temperature.
  Optional rainfall, humidity, wind and radiation override training-reference
  values. The date is automatic. No year/month or model selector is exposed.
- Yield output uses the validation-selected HistGradientBoostingRegressor.
  The Contextual Residual MLP remains an explicitly weaker research comparison.
  Standard preprocessing has 21 numerical and 9 one-hot features; the older
  denoising-autoencoder experiment is not the current default route.
- Results show tonnes/hectare, production, kilograms, optional gross value,
  reactive area/price scenarios, all feature contributions and actual
  preprocessing/calculation steps. Contributions are not causal effects.
- Known district-season pairs use measured training references. Missing pairs
  use the separate neighbour-augmented model, with synthetic provenance shown
  in the prediction flow. Transfer accuracy in unobserved districts is unknown.
- Rice-photo screening runs the ten-class EfficientNet-B0 locally. No district
  is required. Yield context is linked only on request and never changes logits.
  Low-confidence screening is not a confirmed diagnosis. Pixel localisation
  explanations are not implemented; the animated plant is educational only.
- Architecture has mutually exclusive Yield Prediction and Disease
  Identification panels, exact model names, input dimensions, split counts,
  held-out metrics, data sources and inference steps.
- One black-only visual theme and one UI font. No cloud API or Google Font is
  required. WebGL/Edge WebView2 hardware acceleration is needed for the 3D view.

## Data and models

The current measured master has 2,642 rows, 30 columns and 68 matched districts.
Train/validation/test: 1,984 / 321 / 337, split chronologically.
See ../../README.md and ../desktop/README.md for source licences, exact metrics
and limitations. Dataset CSVs are not loaded into the frontend at prediction time;
the portable runtime supplies trained models and train-derived references.

The app's image model is an EfficientNet-B0 fine-tuned on 8,419 duplicate-filtered
Paddy Doctor photos (5,905 / 1,257 / 1,257). Reference photographs in this UI are
display assets, not new independent evaluation samples.

## Checks

```powershell
node APP/tests/test_reference_photos.cjs
node APP/tests/test_architecture.cjs
node APP/tests/test_input_effects.cjs
node APP/tests/test_rice_model.mjs
& OTHER/training_env/Scripts/python.exe -m unittest APP.tests.test_desktop APP.tests.test_recent_yield APP.tests.test_spatial_coverage
```

The installer build also runs the reference-photo test against its staged site.
Credentials, raw competition photographs, virtual environments, training runs
and private demo photos must never be bundled or committed.
