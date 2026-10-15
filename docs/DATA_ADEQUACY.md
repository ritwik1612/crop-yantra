# Yield-data adequacy check — 15 October 2026

## Current evidence

- Original source-derived master: **2,018 observations**, covering 60 geographic
  districts. Training: 1,485 rows; validation: 245; test: 288.
- Augmented table: **3,363 rows**, including 1,345 nearest-district estimates.
  About 40% of its rows are estimates derived from existing training evidence,
  not additional independent observed outcomes.
- Standard representation: 28 predictors; DAE representation: 16 predictors.
- No MLP or HistGradientBoostingRegressor accuracy result is available yet.

This is usable for a prototype and initial small-model experiments. Row count
alone cannot demonstrate accurate forecasts or generalisation to every district.
No fixed number of rows guarantees accuracy. Acceptable error must also be
defined for the intended use and evaluated on real held-out observations.

## Read-only diagnostic baseline

Use the latest **original training** yield through 2015 for each district/season.
If that pair is absent, use the original training global mean. No augmented
rows or held-out labels contribute to prediction construction.

| Partition | Rows | MAE (t/ha) | RMSE (t/ha) | R² | Global-mean fallback rows |
| --- | ---: | ---: | ---: | ---: | ---: |
| Validation 2016–2017 | 245 | 0.8500 | 1.0878 | -0.0316 | 71 |
| Test 2018–2019 | 288 | 0.8644 | 1.0266 | -0.2706 | 145 |

This is a persistence/mean baseline, **not** the trained proposed model. It
shows that an assumption of reliable historical persistence is not supported.
Negative R² means its squared error is worse than the partition-mean constant
benchmark. It does not establish the best achievable accuracy with weather
features or prove that the dataset is unusable.

Reproduce with `python APP/training/audit_data.py`. This audit changes no data,
fits no main model and writes no model weights. Do not repeatedly tune against
the reported test result; choose settings with validation only.

## Additional real source records already present

The preserved government file contains these valid rice/paddy area-production
records (positive area, nonnegative finite production):

| State / UT | Candidate records | Source years |
| --- | ---: | --- |
| Andhra Pradesh | 893 | 1997–2019 |
| Karnataka | 1,538 | 1997–2019 |
| Kerala | 899 | 1998–2019 |
| Puducherry | 151 | 1998–2019 |
| Tamil Nadu | 821 | 1998–2019 |
| Telangana | 302 | 2013–2019 |
| Total | 4,604 | Mixed district vintages |

These are **candidates, not 4,604 additional training-ready rows**: the current
2,018 are drawn from this source, district names/boundaries change, some years
have no matching preserved weather, and Kerala/Puducherry are excluded by the
current builder. Never append them as duplicates or silently fill their weather
with unrelated district measurements.

## Decision

Do not add more interpolated rows just to increase sample size. First benchmark
MLP and boosted trees on genuine held-out labels, compare learning curves on
fixed validation years, and run geographic holdouts before claiming unseen-
district performance. A target-specific uncertainty/abstention method needs
separate calibration and validation.

If those checks show insufficient performance, expand with the unused real
crop records after reviewed district aliases/split handling and matching
[NASA POWER weather](https://power.larc.nasa.gov/docs/services/api/temporal/daily/).
Rebuild a versioned master and fit preprocessing on its training partition only.
This audit has not completed that source-recovery/weather-acquisition work and
does not claim that the dataset has become more accurate.

## Image component

Selected source: [Paddy Doctor on Kaggle](https://www.kaggle.com/competitions/paddy-disease-classification/data).
The complete competition data page lists approximately **1.09 GB**. Our proposed
four-class, up-to-1,600-image subset has not been downloaded or packaged, so its
actual file size and a separate subset download link do not exist yet. Below
200 MB remains a working-set budget after resizing, not a measured archive size.
Kaggle sign-in and acceptance of competition rules may be required to download.
