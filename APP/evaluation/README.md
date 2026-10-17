# Trained-model evaluation

`evaluate_models.py` loads the fixed validation-selected yield bundle and the
saved EfficientNet-B0 checkpoint. It reproduces held-out metrics, breaks yield
results down by state/season/year/weather quartiles, measures validation-set
permutation importance, and scores the same held-out photos under fixed image
perturbations. It does not retrain, select another checkpoint, tune thresholds,
activate app inference or modify source datasets.

Outputs are a Markdown report, JSON diagnostics and two scientific figures.
The private demo-photo folder has class-organized seeded examples, explicitly
marked failures, hashes and labels. It has no invented season labels. These are
known held-out examples, not a new independent evaluation set.

Run in the installed training environment. Existing audit/demo directories are
protected; provide new paths to repeat without replacing an earlier audit:

```powershell
& './OTHER/training_env/Scripts/python.exe' APP/evaluation/evaluate_models.py --output docs/evaluation/repeat_audit --demo-dir 'DATASET/images/testong images repeat'
```

Model fitting and selection are deliberately outside this script. After using
these errors to change a model, reserve new independent test data before claiming
new generalization performance. Do not publish third-party demo photos without
checking their source permissions.
