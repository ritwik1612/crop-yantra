# Changelog

## 0.6.0 — 2026-10-20

- Added locally generated, typeset PDF exports for yield, crop health or both.
  Reports use the dark Paddy theme, include the user's screening photo, exact
  area/price calculations, model contributions, class scores and limitations.
- Export snapshots are matched to result IDs so stale predictions or a previous
  photo cannot silently be included. A native Save dialog chooses the destination.
- Photos are kept in memory for screening/export; they are not uploaded.
  Saving a crop-health PDF explicitly embeds the selected photo without EXIF.
- The unreleased 0.5.1 icon correction is included in this release:

- Bundled the approved multi-resolution rice ICO for the native window instead
  of relying on executable-icon extraction. Set taskbar identity before GUI startup.
- Assigned the same explicit ICO to Start Menu and optional desktop shortcuts.
  Preserved Paddy.Desktop.1 so upgrades retain the same application identity.
- Added native-icon, ICO-size and installer-shortcut regression checks.

## 0.5.0 — 2026-10-20

- Fixed all ten offline Real photo views: replaced seven excluded local-only
  examples with correctly labelled published photographic panels, retaining
  source citation and CC BY attribution. Added packaged-asset coverage checks.
- Unified results and architecture typography and added live model specifications,
  split/held-out metrics, neural comparison details and result interpretation.

- Added an explicitly educational multi-condition comparison: every leaf has
  a varied symptom example; leaf clicks focus its assigned condition. A whole-
  plant overview and healthy comparison remain available. Dead heart uses a
  dry central-shoot example rather than generic pale paint on one green blade.
- Reorganized the black-only workspace: guided land/weather entry, reactive
  output quantities, selectable architecture diagrams, method panels and
  step-by-step actual prediction audits. Yield/image architecture tabs remain
  mutually exclusive; technical tables remain available under Show all steps.
- Added every tree-feature contribution and an additive, signed input-group
  decomposition checked against baseline + effects = prediction. Shared weather
  features stay separate; land size/date/price roles are explicitly distinguished.
- Moved camera, photo-reference and motion controls below the specimen viewport.
- Replaced the 2.5D photographic plant renderer with an original, connected
  WebGL rice model: four culms, 24 curved/folded leaf meshes, four branched
  panicles and 672 instanced grains. No plant-image billboards are rendered.
- Refined asymmetric culm heights, tapered stems, variable leaf dimensions and
  twist, epidermis albedo/bump detail, secondary panicle branches, pointed husks
  and varied individual grain proportions, orientation and ripeness colour.
- Added real camera orbit, leaf-normal-facing inspection, plant-space symptom
  shaders and pointer-gust sway. Opaque foliage is preserved; ray-tested camera
  approaches and dedicated inspection lighting improve symptom visibility.
  Three.js r170 and its MIT notice are bundled locally for offline use.
- Added a geometry/export test and a portable Three.js JSON model snapshot.
  The model is educational; visual symptoms are not diagnostic model evidence.

## 0.4.0 — 2026-10-19

- Replaced detached leaf swapping with one connected rice specimen. Each
  inspection point now has a shared plant-space symptom region and camera
  focus/zoom/roll/tilt preset. Scroll and selector animate between these views.
  This remains a 2.5D educational visual, not a reconstructed 3D diagnosis.
- Added ten class-matched animated symptom views, scroll-based inspection,
  cursor-velocity wind with anchored stems, and a separate real-photo dialog
  with zoom, close button, Escape and backdrop dismissal. Local competition
  reference photographs are excluded from Git and block distributable builds
  until redistribution permission or licensed replacements are resolved.
- Rebuilt crop health around a photographic-style rice specimen, circular view
  controls, wind-responsive anchored mesh motion, and full-size real disease
  reference photos with magnification. Generated artwork is not training data or
  model evidence. Animation pauses offscreen and respects reduced-motion settings.
- Added guided land/weather entry, live rice-coverage geometry, and interactive
  architecture model paths. Kept real inference, photo validation, map selection,
  source attribution and mutually exclusive architecture tabs intact.
- Trained a separate geographic coverage tree on 1,984 measured and 3,094
  explicitly synthetic, downweighted training rows. Same-season/year donors
  are restricted to training years <=2020; measured validation/test stay intact.
  Enabled neighbour-based estimates for all 515 map district-season pairs,
  retaining the original predictor for measured-reference pairs. Output includes
  transfer status and auditable donor distances/weights, not a local accuracy claim.
- Reworked the review preview into a black-only, single-font interface. Removed
  the theme toggle, large colored hero panels and author footer. Added interactive
  source-to-dataset inspection, live land-coverage feedback and focused About tabs;
  preserved state/district map controls. Preview remains uninstalled pending review.
- Added total land size, area units and optional rainfall, humidity, wind and
  radiation inputs. Chose the yield model automatically instead of exposing model
  selectors, and distinguished user-supplied inputs from historical defaults.
- Added attributed UPAg/DES rice labels through agricultural year 2024–25 and
  cached missing NASA POWER weather. Current master: 2,642 rows, 68 matched districts.
- Corrected candidate agricultural-year weather windows, including cross-year
  Rabi/Winter and following-year Summer. Exact same-state boundary matches only.
- Retrained standard preprocessing, contextual neural alternatives and boosted
  trees with a 2001–2020 / 2021–2022 / 2023–2024 chronological split.
- Default tree chosen by validation RMSE. Recent test MAE 0.454, RMSE 0.571 t/ha,
  R² 0.269. Neural alternative remained weaker and is marked experimental.
- Replaced historical-year form with map-only location selection, season,
  average-temperature slider and automatic request date. Current-season outputs
  explicitly identify historical weather assumptions and unvalidated forecast scope.
- Enabled photo-only health screening without location. Yield-to-health context
  is linked only through the result action and can be removed.
- Refined the desktop interface with quieter typography, fewer decorative
  badges, flatter surfaces, tighter controls and reduced-motion-aware transitions.
- Added current request calculations, transformed features and reactive production
  scenarios; retained exclusive architecture tabs and image-reference flipping.
- Consolidated 332 demo photos in Testing Images and preserved training-source assets.
- Preserved pre-update runtime/master for rollback; blocked accidental legacy
  pipeline overwrite. No fabricated district labels enter active training.

Earlier releases: see the repository's Git history and GitHub Releases.
