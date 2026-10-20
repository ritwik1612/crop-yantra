# Paddy for Windows — 0.5.1

Offline rice yield scenarios and rice-photo screening by R Ritwik (23BAI0037)
and Joshith G (23BAI0075).

## Install

Run `releases/Paddy-Setup-0.5.1.exe`, or download it from
[GitHub Releases](https://github.com/ritwik1612/crop-yantra/releases/tag/v0.5.1).
The green/off-white installer uses the approved rice silhouette, defaults to
Program Files, permits another destination and creates a Paddy Start menu
shortcut for Windows Search. Administrator approval is required. A desktop
shortcut is optional. Windows 10/11 x64 and Edge WebView2 are required.
The academic installer is unsigned; security warnings require user review.

## Use

1. Select a state and district on the reactive map. There are no duplicate
   State/District dropdowns.
2. Choose season, average seasonal temperature and area. Request date is automatic;
   there are no year/month selectors.
3. Estimate seasonal yield and inspect Show prediction flow. Other weather and
   district-area features use training-season medians. This is a **current-season
   scenario, not a validated live forecast**. It does not retrieve an old yield
   label as the current output.
4. Change output area/price to update production, mass and gross value instantly.
5. For standalone crop health, choose a rice photo; no location is required.
   To link yield context, use Analyse crop health on a completed yield result.
   Use photo only removes the link. Context never changes image logits.

## Models

- Default **HistGradientBoostingRegressor**, chosen by validation RMSE. The
  recent master has 2,642 records and 68 matched districts, through 2024–25.
  Train 1,984 / validation 321 / test 337, chronological 2001–2020 / 2021–2022 /
  2023–2024. Recent test MAE 0.454, RMSE 0.571 t/ha, R² 0.269.
- Experimental **Contextual Residual MLP**: 30 → 64 → 32 → 1 weather branch,
  GELU/dropout and a learned district-season offset. Validation selected no
  year trend. Its exported graph retains a constant-zero reserved year slot.
  Test MAE 0.605, RMSE 0.819 t/ha, R² −0.506: weaker than the tree; not default.
  Standard preprocessing uses 21 numerical and 9 categorical indicator features.
  DAE is an older preserved representation experiment, not the deployed route.
- **EfficientNet-B0**: ten-class rice screening, 8,419 duplicate-filtered photos,
  5,905 train / 1,257 validation / 1,257 test. Test accuracy 85.04%, macro-F1
  83.59%; weakest recall 67.21% for bacterial leaf blight. This includes disease,
  pest-symptom and normal labels; unsupported conditions are not reliably rejected.

All yield parity checks cover 2,642 rows; held-out runtime predictions reproduce
the 337-row evaluation. Historical full-season evaluation does not establish
current-season or farm-level accuracy. Neural sensitivities are reference
occlusions, not additive/causal/SHAP values; tree-path contributions are additive
model explanations, not agronomic causation. No disease-loss percentage is inferred.

## Development and build

From the project root in PowerShell:

```powershell
& OTHER/training_env/Scripts/python.exe -m unittest APP.tests.test_desktop APP.tests.test_recent_yield
node APP/tests/test_health.cjs
node APP/tests/test_architecture.cjs
& OTHER/desktop_env/Scripts/python.exe APP/desktop/build.py
node APP/tests/test_reference_photos.cjs
& OTHER/desktop_env/Scripts/python.exe -m unittest APP.tests.test_branding
& OTHER/paddy_build_0_5_1/dist/Paddy/Paddy.exe --self-test
```

Build uses PyInstaller and Inno Setup 6. Only allowlisted app assets and verified
portable models enter the installer; no raw datasets, virtual environments,
credentials or private demo photos are bundled. Keep installers in Releases,
not Git. `OTHER/model_archive/yield_before_recent_20261019/` preserves rollback
models/master. Mutually exclusive architecture tabs, map interactions, dark
mode and real/illustrated reference-photo flipping remain available offline.

The 332 local demo photos are in the root Testing Images folder. They are demo
copies, not a new independently collected test set. Review its manifest before
using them to make evaluation claims.
