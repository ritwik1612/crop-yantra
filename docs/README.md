# Start here: South India rice yield project

See the [architecture diagrams](architecture/README.md) for the model names
and data flow through preprocessing, training and the proposed application output.

The [dataset feature-transition presentation](presentations/Rice_Dataset_Feature_Transition_Visual.pptx)
shows raw sources, selection, merging, preprocessing, complete standard/DAE
feature lists and training-ready CSV outputs.
The same rendered slides are available as a [PDF](presentations/Rice_Dataset_Feature_Transition_Visual.pdf).

For the faculty pitch, read [Preprocessing_Proposal.pdf](Preprocessing_Proposal.pdf).
See the detailed [raw-source feature selection and merge diagram](figures/Raw_Data_Feature_Selection_and_Merge.png)
for exact source fields, district matching, seasonal alignment and predictor exclusions.
It explains the source merge, feature construction, preprocessing, representation
comparison and proposed models without local file paths.

Read [Crop_Workflow.pdf](Crop_Workflow.pdf) for the full source-to-application
explanation, three workflow diagrams, actual preprocessing findings and plots.
See [MODEL_REGISTRY.md](MODEL_REGISTRY.md) for exact model names and roles,
and [COMPLETION_CHECKLIST.md](COMPLETION_CHECKLIST.md) for the delivery audit.
Open [the prototype](../APP/prototype/index.html), or serve it at localhost:8765.
[Open the maintained preprocessing notebook in Colab](https://colab.research.google.com/github/ritwik1612/south-india-crop-yield-dataset/blob/main/pre-processing/Crop_Preprocessing.ipynb).
It shows the complete current code, saved table previews and seven actual plots.
This replaces the older standalone notebook's superseded flat CSV paths.

## The only active dataset stages

| Folder | Contents | Use |
| --- | --- | --- |
| ../DATASET/raw/ | Three source families; district properties and coordinates are ordinary CSVs | Rebuild the dataset |
| ../DATASET/merged/rice_master.csv | One consolidated master, 2,018 rows x 30 columns | Inspect source-derived observations |
| ../DATASET/training/standard/ | train.csv, validation.csv, test.csv | Conventional-feature experiments |
| ../DATASET/training/autoencoder/ | train.csv, validation.csv, test.csv | DAE-feature experiments |

**Supervised training uses a training CSV, not the raw downloads.**
The two representations use exactly the same rows and original 21 numeric
predictors. The standard representation has 28 predictors (21 numeric + 7
categorical); the DAE representation has 16 (8 latent + 7 categorical + 1
reconstruction error). YIELD is the label; identifier fields are metadata.
See [the training manifest](../DATASET/training/manifest.json) for exact safe
predictor names.

The raw source families are government crop statistics, GADM boundaries and
NASA POWER daily weather. This is a constructed dataset from recorded and
reanalysis data. No simulated observations were added.

## Reproduce

From the project/repository root:

    python -m pip install -r pre-processing/requirements.txt
    python pre-processing/run_pipeline.py --epochs 180
    python pre-processing/verify_outputs.py

The DAE has been run and its checkpoint saved. Supervised GBDT, MLP, LSTM and
1D CNN model definitions are under APP/models/; yield-model training and
the application UI remain future implementation.

For Colab, clone the organized repository, install requirements, and run these
same commands. No local Windows path is required when running the repository.

## Current evidence

Train: 1,485 rows (2001-2015); validation: 245 (2016-2017);
test: 288 (2018-2019). DAE completed 180 epochs and selected epoch 178 using
validation reconstruction MSE 0.07724. This measures reconstruction, not yield
prediction accuracy. Autumn/Winter occur only outside the training period;
their season indicators map to zero under the current unknown-category rule.
Report those seasons separately when evaluating yield prediction.

See [preprocessing/output_validation.json](preprocessing/output_validation.json),
[preprocessing/deep_preprocessing_report.json](preprocessing/deep_preprocessing_report.json),
and [figures/](figures/) for verified outputs.

## Navigation

- APP/: future predictor architectures and application code.
- DATASET/: raw, merged and training stages only.
- pre-processing/: full runnable preprocessing code and fitted artifacts.
- docs/: current guide, plots, reports, sources and reference papers.
- github/: local GitHub repository checkout.
- OTHER/archive/: superseded code/documents/datasets, retained for recovery;
  excluded from active training and GitHub.

Start reading here; do not use historical files in OTHER for training.
