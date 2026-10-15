# Changelog

All notable changes are documented here. This project follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and uses semantic
versioning.

## [Unreleased]

### 2026-10-15 — Data adequacy audit

- Added a read-only persistence-baseline audit and documented genuine sample
  counts, held-out baseline errors and 4,604 raw rice candidate records.
- Distinguished proposed image-subset storage budget from the 1.09 GB source
  competition download. No main model training or accuracy claim was added.

### 2026-10-15 — Nearest-district augmentation

- Added one 30-column augmented table: 2,018 original rows and 1,345 estimates
  covering the 43 missing districts in the 103-district historical map.
- Used three distinct same-year/season donors within 250 km, inverse-distance
  squared weights and original training years only; retained reproducible donor
  records and hashes in a separate manifest.
- Preserved raw data, original master, preprocessing artifacts and held-out
  training/evaluation files. Added independent preservation/calculation tests.

### 2026-10-15 — Dashboard and inline crop health

- Removed district search; retained map selection, dropdowns and map reset.

- Added accessible section-info popups and a complete hypothetical 3 → 2 → 1
  calculation in the results and methodology. Invented inputs/weights are
  explicitly distinguished from the proposed trained MLP and manual demo values.

- Replaced sparse output plots with labelled yield tracks, a continuous area
  scenario chart and a shaded historical series with focusable observations.
- Moved crop health below yield results on the same page; navigation scrolls
  rather than hiding the yield workspace.
- Added synchronized season selection and season/growth-stage rice illustration
  variants. Illustrations are not disease predictions or seasonal prevalence.
- Removed promotional headings and redundant workspace copy. Rice-only scope,
  source attribution and essential pretraining limitations remain visible.

### 2026-10-14 — Visual output dashboard

- Added live what-if yield/area controls and reset. All derived charts, KPI cards,
  formulas, price scenarios and JSON exports react immediately without re-running
  a predictor or changing observed source data.

- Added production-tonnes/kg and area cards, demo-versus-observed yield chart,
  same-season observed yield trend with accessible table, and interactive area scenarios.
- Added optional user-price gross-value calculation. No prices, costs, confidence
  intervals or stress/disease scores are invented. Demo calculations and observed
  history are explicitly distinguished.
- Extended downloaded JSON with computed outputs, source reference/trend and
  scenario/price assumptions. Added arithmetic and missing/ambiguous-data tests.

### 2026-10-14 — RYP webpage and training preparation

- Renamed the beta RYP (Rice Yield Prediction) and added a rice-plant silhouette logo/favicon.
- Added source-derived white state map, hover lift, state zoom, all 103
  selectable source-vintage districts, search, keyboard access and pan/zoom.
- Added an Info page with a persistent global black-background dark theme.
- Added demo-result derivation, calculation JSON download and separately labelled
  historical observations. Changing inputs clears stale results.
- Added check-only training readiness, explicit future four-experiment training,
  model export contracts and saved-preprocessing inference modules. No yield
  model training was run; PyTorch/scikit-learn fitting and inference still need
  a compatible environment and execution verification.

### Changed

- 2026-10-11: Synchronized active root project files to the public repository,
  including boundary CSV conversion, the updated visible-code notebook, APP beta,
  faculty proposal and dataset feature presentations.
- Expanded the repository README with source provenance, all feature groups,
  dataset splits, representation differences, model roles, setup and limitations.

### Architecture documentation

- Added three reproducible SVG/PNG diagrams for data preprocessing, model training
  and the proposed application flow. Completed and proposed stages are distinguished.

### Added

- Updated the Colab notebook to embed the exact merge and preprocessing modules,
  match the presentation's predictor lists, explain the DAE rationale, and check
  both representation schemas and all six output row counts. Existing saved
  preprocessing results remain labelled as the 08 October run.

- Added five editable flow diagrams to the dataset presentation and exported
  the same 25 rendered slides as a PDF alongside the PowerPoint.

- Dataset-only PowerPoint covering raw sources, selected features, district and
  season joins, standard and DAE feature transformations, complete preprocessed
  predictor lists, representation differences, and all six training-ready CSVs.

- Detailed raw-source feature selection and district/year/season merge diagram.
- Ordinary district and boundary-coordinate CSVs replacing the active GADM ZIP.
  Verified all 676 district records and 275,432 ordered vertices against the source.
  The builder now reads district CSV coordinates; the 2,018-row master is unchanged.

- Expanded the faculty proposal with exact supervised and future sequence model
  architectures, predictor inputs, proposed learning procedures, evaluation rules
  and a user-to-prediction inference diagram. Yield model training remains proposed.

- Faculty-facing LaTeX preprocessing and proposed-model PDF with source links,
  four workflow diagrams, both student names and a merged-versus-preprocessed
  comparison. It separates verified preprocessing results from proposed yield experiments.

## [0.2.0] - 2026-10-08

### Changed

- Streamlined active data into raw/, merged/ and training/ with readable filenames.
- Rebuilt the 2,018-row master directly from three preserved raw sources; join tables are temporary.
- Conventional and DAE representations now use the same 21 original numeric predictors.
- Executed and verified conventional preprocessing and the 180-epoch DAE run.
- Saved preprocessing artifacts, six split CSVs, predictor manifest, plots and measured findings.
- Archived superseded implementation, scripts, documents and dataset packages outside active use.
- Added exact GBDT, MLP, LSTM and 1D CNN architecture definitions; supervised yield training remains future work.
- Added the green/off-white Verdant beta with explicitly illustrative results.
- Added the complete workflow PDF, three vector diagrams, model registry and delivery checklist.
- Added a maintained Colab notebook with complete code, saved verified outputs and seven graphs.

### Added

- Added `Dataset_and_Training_Guide.md` documenting actual source provenance,
  construction rules, DAE inputs, verified cohort counts, preprocessing findings,
  training-file selection, and the distinction between implemented and executed stages.

- Added a `RAW datasets/` source-data inventory with read-only links to the Government of India crop statistics, GADM boundaries, and NASA POWER daily weather used by the pipeline.
- Added automated DL preprocessing scripts: `automated_dl_preprocessing.py` and `deep_preprocess_autoencoder.py`.
- Added deep-learning architecture and raw-versus-preprocessed comparison documentation.
- Added `MASTER_TRAINING_DATASET/` and an automated CSV-only builder that merges the training parameters into one source-backed rice-yield table.
- Documented the preprocessing model as the established Denoising Autoencoder (Vincent et al., ICML 2008), rather than a newly proposed architecture.
- Aligned automated DL preprocessing with the consolidated master training dataset and documented its 21 non-leaking DAE inputs, encoded contextual inputs, target, and exclusions.

### Planned

- Geospatial tiling with coordinate-preserving output.
- Mixed RGB/multispectral fusion experiments.
- Experiment tracking integrations and deployment profiles.

## [0.1.0] - 2026-08-06

### Added

- Initial Python package and command-line interface.
- ResNet/MobileNet classification and U-Net segmentation pipelines.
- Classification and paired-mask datasets with deterministic splitting.
- NDVI generation for red and near-infrared raster bands.
- Dataset indexing and validation commands.
- Training checkpoints, JSON history, and inference commands.
- Unit tests, sample configurations, architecture notes, and dataset guidance.
# 2026-09-24

- Added `South_India_Preprocessing_Report.tex`: a Computer Modern academic LaTeX report covering data provenance, files, features, preprocessing methods, outputs, quality findings, and modelling implications.
- Compiled and visually verified `South_India_Preprocessing_Report.pdf` (four A4 pages).
# 2026-10-15 — Crop Yantra pretraining demo

- Renamed the GitHub repository to crop-yantra and updated active source links.
- Added general rice disease references, labelled illustrative leaf placeholders,
  shared yield context, local photo preview and metadata-only request export.
- Documented a compact Tamil Nadu rice-image subset and EfficientNet-B0 plan;
  no image model training or diagnosis is claimed.
- Added static Vercel deployment configuration with environment-file exclusions.

