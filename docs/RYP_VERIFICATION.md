# RYP verification — 14 October 2026

Story: state map → state zoom → district selection → synchronized crop context →
explicitly illustrative result → calculation explanation and methodology page.
No API, live weather service or trained yield inference is part of this beta.

| Boundary | Evidence |
| --- | --- |
| Source CSV → browser asset | 103 districts; 60 covered; all 2,018 observations accounted for; three unit tests passed |
| Map → form | Browser clicks on Karnataka/Mandya and Tamil Nadu/Thanjavur synchronized state and district controls |
| Form → preview | 12 ha × fixed 4.20 t/ha returned 50.4 t, with explicit demo explanation |
| Inputs → stale output | Changing crop year hid the previous result |
| Info → global theme | Browser computed body background rgb(0,0,0) after dark-mode switch |
| Responsive layout | Phone viewport tested at 390 × 844; effective document width and scroll width both 375 px (no horizontal overflow) |
| Browser console | No application warnings/errors observed at final check |
| Training input contract | Six partitions checked; 1,485/245/288 rows, 28/16 predictors, aligned labels/keys, disjoint chronological splits |

## Not executed or not implemented

- Supervised training was deliberately not run.
- MLP/tree fitting and saved-inference execution await compatible PyTorch and
  scikit-learn installation. The current bundled Python runtime lacks them.
- Future inference modules require a complete feature row, not just user map
  inputs. Weather/area-context feature construction and browser API integration
  remain to be implemented before live prediction.
- Neural multi-seed aggregation, reconstruction-score ablation, calibrated
  uncertainty and feature attribution are not provided yet.

Existing raw, merged and training CSVs were not modified during this UI work.

## Live visual outputs

Output arithmetic tests passed, including unavailable/ambiguous history,
future-year exclusion, zero price/yield and invalid area/price/scenario input.
Browser changes of demo yield to 12 t/ha, area to 20 ha and price to ₹20/kg
immediately returned 240 t, 240,000 kg and ₹4,800,000. Moving the scenario slider
to 150% returned 360 t with a chart marker. The observed label stayed unchanged.
No trained predictor or weather service was run. Gross value is not profit.

The phone-width black theme also updated successfully: 15 ha at 4.2 t/ha
produced 63 t and ₹1,260,000 at the QA-supplied ₹20/kg price. Effective document
width and scroll width both remained 375 px, with no horizontal overflow.
