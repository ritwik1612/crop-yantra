# RYP — Rice Yield Prediction

A responsive pretraining webpage with white cartography, state hover lift,
animated state zoom, clickable district partitions, search, synchronized form
controls, pan/zoom and keyboard district navigation. A rice-plant silhouette
provides the header identity and favicon.

Open index.html directly, or serve from the repository root:

```bash
python -m http.server 8765 --bind 127.0.0.1 --directory APP/prototype
```

Visit http://127.0.0.1:8765. No Node build, API key, map service or frontend
dependency installation is needed. Optional Google Fonts have system fallbacks.

1. Click a state (hover enlarges its white silhouette slightly).
2. Click a district, or use district search/dropdowns. Back to South India
   restores the overview. Drag to pan; buttons zoom; Ctrl-scroll zooms.
3. Set season/year/area and choose a proposed representation/predictor.
4. Preview the result. Its explanation shows the exact calculation and which
   stages are proposed rather than executed. Input changes clear stale results.
5. Project info opens sources, preprocessing, model names and output methodology.
   Its appearance switch turns **the entire site** black-background dark or light.
   Theme preference is retained locally where browser storage is available.

The map exposes **103 source-vintage GADM districts** across AP, Karnataka,
Tamil Nadu, Telangana, Kerala and Puducherry. All are selectable, but only 60
have observations in the historical cohort. Dataset boundaries are GADM 4.1;
they do not include every modern renamed/newly subdivided district. Kerala and
Puducherry are map context, not newly added training data. Historical-state
crosswalk records remain labelled with their actual source state.

## Honest preview output

The result dashboard includes production (tonnes and kilograms), entered area,
observed yield reference, demo/observed comparison bars, same-season historical
yield trend/table, and interactive area scenarios. Historical charts include
only records through the selected crop year; ambiguous year matches are excluded.
An optional user-supplied ₹/kg price computes **gross value**, not profit, and
updates a three-price scenario chart immediately. No
default market price is assumed. The scenario slider changes arithmetic area,
not yield, and does not represent an uncertainty interval. Downloaded JSON
retains these outputs and assumptions. Empty history stays visibly unavailable.

Run `node APP/tests/test_outputs.cjs` from the repository root for output logic tests.

Yield starts at **4.20 t/ha as an illustrative placeholder**. Live what-if
controls let users change this assumption and the cultivation area. Every KPI,
chart and calculation reacts instantly. Demo production is the chosen demo yield
× entered hectares; reset restores default yield and the original area. The
0–12 t/ha slider is an interface range, not a validated agronomic range.
Representation/model selections change the displayed proposed pipeline,
not the demo yield. The page runs no neural network, weather
fetch, preprocessing transform or trained regressor.

When exactly one historical district/year/season observation matches, its actual
yield and weather summaries are shown separately as **observed, not predicted**.
Historical district area is distinct from entered area. No missing weather is
invented. Download JSON records inputs, demo mode and the calculation explicitly.
No confidence interval or feature-contribution values are fabricated.

## Data asset reproducibility

The checked-in data.js loads without fetch, so the beta also works via file://.
It includes source-derived display geometry and historical context, not model
weights or secrets. Rebuild it only when preserved source/master data changes:

```bash
python -m pip install -r APP/tools/requirements.txt
python APP/tools/build_ui_data.py
```

The builder reads boundary/district/master CSVs unchanged, dissolves district
rings into state outlines for overview, and keeps district rings for zoom view.
GADM attribution/usage terms apply: https://gadm.org/license.html.

See ../training/README.md for training readiness, four future experiments,
saved-model contracts and outstanding live-inference work. No yield training
has been performed as part of this UI update.
