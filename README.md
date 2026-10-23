# Paddy — Rice Yield & Crop Health

Offline Windows research application by **R Ritwik (23BAI0037)** and
**Joshith G (23BAI0075)**. No Vercel deployment or cloud inference.

[Windows installer](https://github.com/ritwik1612/crop-yantra/releases/download/v0.7.0/Paddy-Setup-0.7.0.exe)
· [Desktop build instructions](APP/desktop/README.md)
· [Dataset guide](DATASET/README.md)

## Version 0.7.0 — neural prediction routes

**CNN–LSTM** now predicts yield; **EfficientNet-B0** classifies rice photographs.
Both primary prediction tasks use deep learning. Trees are archived benchmarks,
not app inference or a hidden fallback. DAE and Residual MLP are research artifacts.

LSTM, masked 1D CNN and CNN–LSTM were each trained with two seeds. Validation
selected CNN–LSTM seed 42, epoch 9. Its held-out test MAE is **0.474861 t/ha**,
RMSE **0.599986 t/ha**, R² **0.191802**. This is modest performance, not a claim
of superior accuracy over trees; the old tree uses different full-season inputs.

Preparation reconciles all 2,642 measured rows against raw daily weather.
Chronological splits are 1,984/321/337 rows, with training-only scaling and
weather cut off 60 days before proxy season end. Ten-day bins contain ten
weather variables plus bin-day count. The static branch has two coordinates,
four state flags and five season flags. No generated yield labels are used.

The offline form constructs **scenarios** from training-only weather templates
and user assumptions, not a live observed weather feed. Missing district-season
weather references use geographically nearby training templates, with donor
provenance visible. No local accuracy is claimed for transferred references.

Architecture shows a connected tensor-level diagram, timestep inputs, CNN/LSTM
dimensions and the regression/production calculation. After inference, expand
each stage's latest-run section for actual tensors and hidden activations.
These activations and reference-occlusion sensitivities are not causal weights.
See [sequence training and limitations](APP/training/SEQUENCE_TRAINING.md).

## Previous version 0.6.2 (archived tree route)

This historical section describes the previous app, not the 0.7.0 neural route.
Results then showed actual state flags, split counts and an example tree path.
Signed t/ha contributions are not state training-data shares or fixed weights;
geographic reference blending is explained separately.

Crop-health results use high-contrast proportional score bars. Dark tracks show
the full range, green fills show each score, and the leading class is highlighted.
Model weights and evaluation metrics are unchanged.

Use **Export PDF** on Results to save a formatted yield report, crop-health report
with your uploaded photo, or a combined report. These are typeset documents,
not webpage screenshots. Exports include actual results, inputs, calculations,
model explanations and limitations; the Save dialog chooses the destination.

The native window and Windows shortcuts explicitly use the approved rice logo,
including small taskbar icon sizes. Prediction models and data are unchanged.

The local review preview now uses a true WebGL rice model, not photographic
billboards: connected culms, curved leaf surfaces and branched grain heads.
Dragging orbits in 3D; scrolling focuses an attached leaf, and the camera faces
its surface. Symptom shaders are educational, separate from photo inference.
See [model details](APP/prototype/assets/RICE_MODEL.md). Results and architecture
use consistent typography, live model specifications and step-by-step input audits.
All ten Real photo references are bundled offline with source attribution;
see [photo credits](APP/prototype/assets/PHOTO_CREDITS.md).

- Select location only through the reactive state/district map.
- Select season, average seasonal temperature (10–40 °C) and cultivation area.
  Today's date is automatic; there is no year/month selector.
- Run a **current-season scenario**, not a lookup of an old yield label.
  Missing weather inputs use training-season medians. This is **not a validated
  live-weather or farm-level forecast**. Temperature modifies actual model
  features and dependent scenario quantities, not merely the displayed text.
- Show calculation, transformed inputs and feature contributions on the output
  page. Area and optional price update production/mass/value immediately.
- Photo-only screening requires **no district**. Use “Analyse crop health” from
  a yield result to explicitly link its context; context never changes image logits.
- Architecture has separate, mutually exclusive yield and image tabs.
- All 103 map districts and five seasons have an estimate route. Missing local
  references use a separately trained neighbour-augmented tree model, with a
  visible neighbour-based status and donor details in the prediction flow.
  These estimates are synthetic geographic transfers, not measured local labels.

### Geographic coverage training

`APP/training/train_spatial_coverage.py` builds 3,094 deterministic synthetic
training rows from three geographically nearest same-season, same-year donors
from 2001–2020 only. It trains a separate HistGradientBoostingRegressor using
1,984 measured rows plus the downweighted synthetic rows. Four configurations
are selected using measured 2021–2022 validation only. Selected synthetic sample
weight: 0.1. The original measured-data predictor remains active for known pairs.

The coverage model's measured 2023–2024 test MAE is 0.4403 t/ha, RMSE 0.5547,
R² 0.3093. This does **not** measure accuracy in missing districts, and it is
not used to claim improvement in current-season forecasts. Cross-state donors
are used where nearest same-season records require them. The map is GADM 4.1,
not a current administrative district registry.

## Measured yield data and evaluation

The current master contains **2,642 rows, 30 columns and 68 matched districts**
across Andhra Pradesh, Karnataka, Tamil Nadu and Telangana, with crop-start
years 2001–2024 (through agricultural year 2024–25).

Sources are original government area/production statistics, the
[UPAg/DES dataset mirrored by India Data Portal](https://ckandev.indiadataportal.com/dataset/area-production-yield-apy),
[GADM boundaries](https://gadm.org/data.html), and
[NASA POWER weather](https://power.larc.nasa.gov/docs/services/api/temporal/daily/).
The UPAg mirror carries the Open Data Commons Attribution License. Preserve
the individual sources' terms, including [GADM's license](https://gadm.org/license.html).

Recent source yield is reported in kg/ha; training yield is calculated consistently
as production tonnes / area hectares. Exact normalized same-state district joins
exclude unmatched/newly split districts rather than assigning a parent's label.
Season windows are proxies, not measured sowing dates. Rabi and Winter cross
the agricultural-year boundary; Summer uses March–June of the following year.
Only complete weather windows are retained. NASA EVLAND is land evaporation,
not FAO-56 reference evapotranspiration; radiation uses kWh/m²/day.

Train: **1,984 rows (2001–2020)**; validation: **321 (2021–2022)**;
test: **337 (2023–2024)**. Fit imputation/scaling/encoding only on training data;
select configurations using validation, then evaluate held-out test. These scores
are district-scale evaluations, not live forecast accuracy. CNN–LSTM uses a
60-day-truncated weather prefix; archived comparisons use full-season inputs.

| Predictor | Test MAE t/ha | Test RMSE t/ha | Test R² | Deployment |
| --- | ---: | ---: | ---: | --- |
| CNN–LSTM | 0.475 | 0.600 | 0.192 | Active neural yield route |
| HistGradientBoostingRegressor | 0.454 | 0.571 | 0.269 | Archived full-season benchmark |
| Contextual Residual MLP | 0.605 | 0.819 | −0.506 | Archived full-season neural comparison |

The earlier Residual MLP candidate did **not** outperform the tree. Its branch is
30 → 64 → 32 → 1 with GELU/dropout and a learned district-season offset.
Validation selected the no-year-trend candidate; its exported graph retains a
constant-zero year slot for compatibility. Standard features are 21 numerical
and 9 one-hot indicators. Production and YIELD are excluded from predictors.
DAE is a preserved older comparison, not the deployed preprocessing route.
New scores are not directly comparable to the old 2018–2019 evaluation because
the cohort, chronology, district matching and weather alignment changed.

## Image model

**EfficientNet-B0**, ImageNet initialized and fine-tuned on 8,419 duplicate-filtered
Paddy Doctor rice images: 5,905 train / 1,257 validation / 1,257 test.
Test accuracy **85.04%**, macro-F1 **83.59%**. Ten labels include disease,
pest-symptom and normal classes. Unsupported crops/conditions are not reliably
rejected; model scores are not calibrated diagnostic confidence. District/season
are not classifier inputs. No disease-related yield loss is inferred.

## Files and reproducibility

- `APP/`: application, training and data-maintenance code.
- `DATASET/raw/`: unchanged original sources, recent UPAg source CSV and NASA responses.
- `DATASET/merged/rice_master.csv`: current measured-source master.
- `DATASET/training/sequences_lead60/`: active train/validation/test tensors,
  observation keys and train-fit scaling manifest.
- `APP/training/runs/sequences_20261023_cpu/`: frozen local checkpoints/results.
- `DATASET/training/recent/standard/`: archived full-season tabular comparison CSVs.
- `APP/prototype/runtime/`: verified portable models and inference metadata.
- `docs/architecture/*.mmd`: detailed editable Mermaid data/training/inference flows.
- `Testing Images/`: 332 local demonstration photos; not a new independent test set.
- `OTHER/model_archive/`: rollback assets and rejected experiments, not training inputs.

Acquisition: `APP/tools/download_recent_yield.py`; weather/merge:
`APP/tools/extend_yield_data.py`; fitting: `APP/training/train_recent_yield.py`;
verified activation: `APP/tools/activate_recent_yield.py`.
Training deliberately refuses to overwrite a completed candidate checkpoint.
The older `pre-processing/run_pipeline.py` requires `--legacy-baseline` so it
cannot silently overwrite the newer master. Old standard/DAE partitions and
neighbour-generated experiments remain separate; they are not the active inputs.

Use GitHub Releases for installers; do not commit binaries, credentials, virtual
environments or private demo photos. Raw image archives are not bundled in the app.
