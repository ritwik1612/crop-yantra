# One master dataset

rice_master.csv is the active measured merged CSV: 2,642 rows and 30 columns,
68 same-state matched districts, crop-start years 2001–2024 (through 2024–25).
One row is a rice district-crop-year-season observation.

The original build_dataset.py joins crop area/production, GADM-matched district
coordinates and NASA POWER weather; derives yield, area fraction, seasonal
weather summaries, GDD and five additional predictors. Join products are
temporary and disappear after a successful build. APP/tools/extend_yield_data.py
extends this cohort with attributed UPAg/DES records and complete seasonal
NASA POWER windows. Excluded-row provenance is retained in candidates/recent_yield.

The file preserves YIELD as target and PRODUCTION_TONNES as provenance.
PRODUCTION_TONNES must not be supplied to a yield predictor.
District identity, year and match status are metadata, not encoder inputs.
STATE and SEASON are contextual categorical inputs.

The 21 numeric predictors are listed in ../training/recent/manifest.json and the
preprocessing artifact manifests. The original numeric features are retained
here even though the DAE export compresses them into latent features.
