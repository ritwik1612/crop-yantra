# Dataset guide

## Active yield data

- **Master:** `merged/rice_master.csv` — 2,642 source-derived records, 30 columns,
  68 same-state matched districts, crop-start years 2001–2024 (through 2024–25).
- **Training:** `training/recent/standard/train.csv` — 1,984 rows, 2001–2020.
- **Validation:** `training/recent/standard/validation.csv` — 321 rows, 2021–2022.
- **Test:** `training/recent/standard/test.csv` — 337 rows, 2023–2024.
- **Contract:** `training/recent/manifest.json`. Thirty standard predictors:
  21 numerical + 9 state/season indicators. YIELD is the target, never a predictor.
- **Fitted preprocessor/checkpoints:** `../APP/training/runs/recent_yield_20261019/`.

The candidate builder also keeps a staging copy in `candidates/recent_yield/`,
its manifest and excluded-row ledger. This is the same master, not additional
training observations. The pre-update master/runtime are archived under OTHER
for rollback. Do not concatenate old and recent training exports.

## Separate synthetic coverage data

`candidates/spatial_coverage/synthetic_train.csv` contains 3,094 synthetic rows;
`combined_train.csv` contains those plus 1,984 original training rows. Neither
file overwrites the measured master or measured validation/test data. The
separate coverage model uses the combined file's equivalent in-memory rows.

Every generated row records DATA_ORIGIN, donor record keys, distances, normalized
weights and whether transfer crosses a state boundary. Donors are three nearest
available districts in the same crop season and year, restricted to <=2020.
Yield and covariates are inverse-distance weighted, target coordinates are from
GADM, and dependent quantities are recomputed. Area/weather are proxies, not new
measurements. No random noise or invented future years inflate the dataset.

Validation (321 rows) and test (337 rows) remain measured-only and unchanged.
The measured master retains 2,642 rows; synthetic coverage is not added to that
count. Its 289 missing district-season combinations supplement measured routes
to cover 103 map districts × 5 seasons. Missing-district accuracy is unmeasured.

## Raw sources

1. `raw/government/crop_statistics.csv`: preserved original district/crop/year/
   season area and production observations, used through 2019.
2. `raw/government/upag/cropwise_area_production_yield.csv`: unchanged 16,945,448-byte
   UPAg/DES source mirror, downloaded from India Data Portal. Contains all crops;
   2,815 rice rows for the four states span 2013–14 to 2024–25. Only post-2019
   labels extend the original source, so overlap is not duplicated.
   `provenance.json` records publisher, source URL, license, SHA256 and units.
3. `raw/boundaries/india_districts.csv` and `boundary_coordinates.csv`: one GADM
   source represented as properties and full geometry vertices. Source-vintage
   district names are not today's complete administrative registry.
4. `raw/weather/daily_weather.csv`: preserved 2001–2023 daily NASA extract.
   `raw/weather/nasa_recent/`: cached original NASA API JSON responses supplying
   missing recent years/locations through 2025.

Government records and their UPAg extension form one source family, boundaries
another, weather a third. Attribution:
[original crop catalogue](https://data.gov.in/resource/district-wise-season-wise-crop-production-statistics-1997),
[UPAg/DES via India Data Portal](https://ckandev.indiadataportal.com/dataset/area-production-yield-apy)
(Open Data Commons Attribution License), [GADM](https://gadm.org/data.html) and
[license](https://gadm.org/license.html), [NASA POWER](https://power.larc.nasa.gov/docs/services/api/temporal/daily/).

## Merge and limits

Yield = production tonnes / area hectares. The UPAg reported yield column is
kg/ha and is not copied directly into the tonnes/ha target. Match normalized
district names within the same state only. Do not assign a parent district's
label to its newly split children. Missing matches are excluded and logged.

Agricultural start year labels the season. Rabi uses November–April across the
year boundary; Winter December–March; Summer March–June in the following year.
Kharif uses June–November, Autumn September–December. These broad seasonal
windows are proxies, not measured crop calendars. Require complete daily
weather windows. Coordinates are boundary-vertex averages, not area-weighted
centroids. EVLAND is land evaporation, not reference ET0; radiation uses kWh/m².

`training/standard/`, `training/autoencoder/` and the original root training
manifest preserve the older 2001–2019 experiment. They are **not the current
model inputs**. `augmented/` is a neighbour-generated experiment and is not used
by either currently deployed yield predictor. No synthetic district labels are
silently mixed into the active master.

## Image data

- `images/source/paddy-disease-classification.zip`: official unchanged archive,
  1,093,378,623 bytes. `train.csv` is the original 10,407-row label/variety/age table.
- `images/prepared/paddy_doctor_10class/`: 8,419 duplicate-filtered photos and
  immutable manifest: 5,905 train / 1,257 validation / 1,257 test.
- `images/prepared/paddy_doctor_4class/`: preserved older 1,600-photo comparison.
- `../Testing Images/`: 332 local demo copies, separated from training sources.
  Demonstration reuse does not create independent evaluation data.

Pretrained weights, fitted transforms and model binaries are software/model
artifacts, not extra datasets. Libraries stay under OTHER, not DATASET.

## Reproduce

Use `APP/tools/download_recent_yield.py` for source acquisition,
`APP/tools/extend_yield_data.py` for the candidate master/weather caches,
`APP/training/train_recent_yield.py` for fitted transforms and supervised models,
and `APP/tools/activate_recent_yield.py` only after validation/export checks.
The legacy preprocessing runner requires explicit `--legacy-baseline` because
it would otherwise replace the new master with the older experiment.
