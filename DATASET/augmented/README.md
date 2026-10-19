# District-augmented rice table

**Archived experiment, not the active training table.** This table was built
from the former 2,018-row master; the active measured master now has 2,642 rows.
The original manifest is retained unchanged as historical provenance. Its
source_csv records the path at generation time, not today's file contents.
The former source is preserved under OTHER/model_archive/yield_before_recent_20261019.
Current geographic coverage training uses the separate candidates/spatial_coverage
tables described in ../README.md. Do not concatenate these two experiments.

`rice_master_augmented.csv` is one continuous table with the same **30 columns**
as the original master. It contains **3,363 rows**: the original 2,018 records
plus 1,345 nearest-district estimates for 43 previously unrepresented map
districts. No extra classification/flag column was added. `MATCH_STATUS` remains
an existing provenance field.

The result covers all **103 source-vintage GADM 4.1 map districts**, including
Kerala and Puducherry. This is not a claim of measured coverage or coverage of
all present-day administrative districts. Generated values are not observations
of the target district or evidence of rice cultivation there.

## Construction

- Started from the former, unchanged 2,018-row `merged/rice_master.csv` snapshot.
- For each missing map district and available year/season, select three distinct
  donor districts with the nearest representative coordinates, within 250 km.
- Donors must be from the same year and season, limited to 2001–2015 and
  Kharif/Rabi/Summer. Exclude ambiguous duplicate geographic donor groups.
- Compute `w_i = (1 / max(distance_km_i, 1)^2) / sum(inverse distances squared)`.
  Yield, crop-area proxy and seasonal weather proxies are weighted means.
- Use the target district's coordinates. Recalculate production as yield ×
  crop area, temperature range, water balance, GDD ratios and log crop area.
- Leave `AREA_FRACTION` and `WEATHER_DAY_COUNT` empty for added records: there is
  no verified target-state area denominator or observed target weather coverage.
- Add no random noise, no generated donors, no future-year donor information.
- Sort all rows together by state, district, year and season.

Nearby coordinates do not guarantee shared climate, soil, irrigation or crop
management. These estimates are a provisional augmentation experiment, not a
replacement for official district records. Weather and area estimates are
proxies, not independently acquired target-district measurements.

`generation_manifest.json` records exact donor row keys, coordinates' geographic
IDs, distances, weights, output record positions, source/output hashes and
skipped periods. Text-file hashes normalize CRLF to LF, matching Git attributes
and making verification portable across Windows/Linux checkouts.
Reproduce with `pre-processing/augment_districts.mjs` using the
bundled artifact-tool runtime; alternatively configure `ARTIFACT_MODULE_BASE`
to a directory whose node_modules contains `@oai/artifact-tool`.

## Training use

The original master, raw files, fitted preprocessing and training/validation/test
CSVs are unchanged. This table is not automatically loaded by the training runner
or app. Prepare a separate experimental training representation before use.

Use added rows only as experimental training candidates. Never use estimated
labels for validation, test accuracy or proof of all-district generalisation.
Keep real held-out evaluation. Because donors only use the original training
years, existing validation/test labels do not contribute to these estimates.
For new geographic/temporal cross-validation folds, regenerate augmentation
inside each fold using its training donors only. Do not drop provenance or
accidentally use `PRODUCTION_TONNES` as an input to predict `YIELD`.

Sources remain the project's preserved government crop statistics, GADM-derived
coordinates and NASA POWER-derived seasonal weather in the original master.
