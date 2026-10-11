# What the preprocessing contributes

The MAIN chat and implemented pipeline describe rice-yield estimation using
seasonal tabular data. The current work does not train disease diagnosis models.

## Implemented project contribution

1. Integrate government district-season rice statistics, GADM district locations
   and NASA daily weather for four South Indian states.
2. Normalize district names and use a unique-district historical-state crosswalk.
3. Align weather to year/season windows, including previous-year dates for Rabi
   and Winter; retain records with at least 60 complete weather days.
4. Construct 21 numerical features reflecting area, location, coverage, weather,
   accumulated heat, water balance and weather-to-heat ratios.
5. Fit conventional transforms on training years only. Fit a DAE on the same
   scaled numerical inputs without yield supervision, compressing 21 to 8.
6. Preserve categorical state/season context outside the DAE, and export a
   reconstruction-score feature whose usefulness remains to be tested.

## Proposed experiment

Compare standard (28 inputs) and DAE (16 inputs) representations with MLP and
HistGradientBoostingRegressor on identical chronological splits and yield labels.
Evaluate an additional DAE version without reconstruction score (15 inputs),
repeat neural-network seeds, and report state/season results.

This is a reproducible application and empirical evaluation of established
methods on the assembled rice dataset. Supervised yield models remain untrained,
so improved yield accuracy has not been demonstrated. Feature selection follows
domain relevance and leakage prevention; no feature-importance or selection
experiment has proved that every retained input is necessary.

## What cannot be claimed as new

Scaling, one-hot encoding, engineered weather features, chronological evaluation,
and DAE corruption/reconstruction are established methods. DAE training was
published by Vincent et al. in 2008. Feature denoising for crop-yield prediction
also has prior work, including graph spectral denoising; that method differs
from this project's DAE but rules out claiming the general idea as new.

No literature review establishes that this exact combination is first-of-its-kind.
A defensible pitch is: "We build a district-season rice dataset for four South
Indian states and test whether label-free DAE feature learning improves yield
estimation over conventional preprocessing under chronological evaluation."

Sources:
- Project proposal: Preprocessing_Proposal.pdf, sections on features,
  preprocessing, experiment design and current status.
- Vincent et al. (2008), Extracting and Composing Robust Features with
  Denoising Autoencoders: https://icml.cc/2008/papers/592.pdf
- Unsupervised Graph Spectral Feature Denoising for Crop Yield Prediction
  (2022): https://arxiv.org/abs/2208.02714
