"""Create the maintained Colab notebook with visible code and verified saved outputs."""
import base64
import csv
import json
import textwrap
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
cells=[]
def markdown(text): cells.append(dict(cell_type='markdown',metadata={},source=text.splitlines(True)))
def code(text,outputs=None):
    cells.append(dict(cell_type='code',metadata={},execution_count=None,source=text.splitlines(True),outputs=outputs or []))
def display(data):
    return dict(output_type='display_data',metadata={},data=data)

markdown('# South India rice: complete preprocessing\n'
         'Three raw sources → one master CSV → standard and DAE training splits.\n\n'
         'The complete code is visible below. Saved tables and plots are from the verified '
         '08 October 2026 run. Run all cells to reproduce in Colab. This trains the preprocessing '
         'DAE only; it does not train the final yield models.\n\n'
         '**Preprocessing:** SimpleImputer, StandardScaler, OneHotEncoder, Denoising Autoencoder.\n\n'
         'Methods and predictor names match the dataset feature-transition presentation. '
         'The cells install the visible project code below before running it, so a stale '
         'GitHub checkout cannot change the preprocessing methods.')
code('from pathlib import Path\nimport subprocess, sys\n'
     'repo = Path("/content/crop-yantra")\n'
     'dataset_url = "https://github.com/ritwik1612/crop-yantra.git"\n'
     'if not repo.exists():\n    subprocess.run(["git", "clone", dataset_url, str(repo)], check=True)\n'
     'subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(repo / "pre-processing/requirements.txt")], check=True)\n'
     'sys.path.insert(0, str(repo / "pre-processing"))\n'
     'dataset = repo / "DATASET"\n'
     'print("Raw files:", list((dataset / "raw").rglob("*.csv")))\n'
     'print("Master:", dataset / "merged/rice_master.csv")\n')
markdown('## Raw sources and feature selection\n'
         '| Source | Selected fields | Role |\n|---|---|---|\n'
         '| Government | State, District, Crop, Crop_Year, Season, Area, Production | Rice records, identity, area and yield |\n'
         '| GADM | NAME_1, NAME_2, boundary vertices | District matching and representative longitude/latitude |\n'
         '| NASA extract | IDREGION, DATE, TMAX, TMIN, TAVG, VPRES, WSPD, PREC, ET0, RAD, RELH, PS | District-date matching and seasonal weather |\n\n'
         'Filter four states and rice/paddy. Recalculate yield as production divided by area. '
         'Exclude production from predictor inputs to prevent leakage. Raw Yield and IDCOVER are not predictors. '
         'GADM GID_2 links district properties to boundary vertices, while project IDREGION links sources.\n\n'
         'Normalize state/district names, match state plus district first, then allow a unique-district '
         'historical-state crosswalk. Join crop tables on (IDREGION, FYEAR, SEASON). Select daily weather '
         'by IDREGION and the season window. Retain finite yield, matched location and at least 60 complete days.\n\n'
         'Kharif: June–November; Rabi: previous November–April; Summer: March–June; '
         'Autumn: September–December; Winter: previous December–March. These are fixed assumptions. '
         'ET0 is NASA EVLAND land evaporation; RAD totals are kWh/m². District coordinates average boundary vertices.')
markdown('## Visible source code used by this notebook\n'
         'Each writefile cell saves exactly the displayed implementation into the Colab checkout. '
         'The later execution cells run these saved modules. No yield predictor is trained.')
code('from IPython.display import display\n'
     'for relative in ("pre-processing/internal", "pre-processing/artifacts", "docs/figures", "docs/preprocessing"):\n'
     '    (repo / relative).mkdir(parents=True, exist_ok=True)\n')
for relative in ['pre-processing/internal/merge_seasonal.py', 'pre-processing/build_dataset.py',
                 'pre-processing/convert_boundaries_to_csv.py', 'pre-processing/denoising_autoencoder.py',
                 'pre-processing/preprocess_master.py', 'pre-processing/verify_outputs.py',
                 'pre-processing/make_figures.py']:
    markdown('### '+relative.rsplit('/',1)[-1])
    code('%%writefile {repo}/'+relative+'\n'+(ROOT/relative).read_text(encoding='utf-8'))
code('boundary_dir = dataset / "raw/boundaries"\n'
     'if not (boundary_dir / "india_districts.csv").exists():\n'
     '    if not (boundary_dir / "india_districts.geojson.zip").exists():\n'
     '        raise FileNotFoundError("Provide the district CSVs or the original GADM ZIP")\n'
     '    subprocess.run([sys.executable, str(repo / "pre-processing/convert_boundaries_to_csv.py")], check=True)\n'
     'print("Boundary input:", boundary_dir / "india_districts.csv")\n')
markdown('## 1. Build the merged table from the raw files\n'
         'Input: raw/government/crop_statistics.csv, raw/boundaries/india_districts.csv, '
         'raw/weather/daily_weather.csv. Temporary crop/area/location join tables exist only during construction.')
code('subprocess.run([sys.executable, str(repo / "pre-processing/build_dataset.py"), '
     '"--dataset-dir", str(dataset)], check=True)\n')
markdown('## 2. Inspect the master, coverage and missing values\n'
         'A row is a rice district-year-season observation. Yield labels are retained separately from predictors.')
preview='import pandas as pd\nmaster = pd.read_csv(dataset / "merged/rice_master.csv")\n'
preview+='display(master.head())\ndisplay(master.groupby("STATE").size().rename("Rows").to_frame())\n'
preview+='display(master.isna().sum().rename("Missing").to_frame())\nprint(master.shape)\n'
with (ROOT/'DATASET/merged/rice_master.csv').open(newline='',encoding='utf-8') as f:
    rows=list(csv.DictReader(f))
subset=['STATE','DISTRICT','FYEAR','SEASON','YIELD','CROP_AREA','PREC_TOTAL','TAVG_MEAN']
html='<table><thead><tr>'+''.join('<th>'+c+'</th>' for c in subset)+'</tr></thead><tbody>'
html+=''.join('<tr>'+''.join('<td>'+r[c]+'</td>' for c in subset)+'</tr>' for r in rows[:5])+'</tbody></table>'
code(preview,[display({'text/html':html,'text/plain':'Verified master preview: 2,018 rows, 30 columns.'})])
markdown('## 3. Conventional preprocessing — complete code\n'
         'Fit medians, scaling and category mapping on 2001–2015 only. Validation is 2016–2017; '
         'test is 2018–2019. The 21 predictors match the DAE experiment.')
code('artifacts = repo / "pre-processing/artifacts"\n'
     'subprocess.run([sys.executable, str(repo / "pre-processing/preprocess_master.py"), '
     '"--master-path", str(dataset / "merged/rice_master.csv"), '
     '"--output-dir", str(dataset / "training/standard"), "--artifacts-dir", str(artifacts)], check=True)\n')
markdown('## 4. Denoising Autoencoder — complete code\n'
         '21 numeric inputs → 64 → 32 → 8 latent features → 32 → 64 → 21 reconstruction. '
         'Gaussian corruption is added during training. Clean inputs are reconstruction targets. '
         'YIELD and PRODUCTION_TONNES never enter the encoder.')
code('deep = dataset / "training/autoencoder"\n'
     'subprocess.run([sys.executable, str(repo / "pre-processing/denoising_autoencoder.py"), '
     '"--model-ready-path", str(dataset / "merged/rice_master.csv"), '
     '"--output-dir", str(deep), "--epochs", "180", "--latent-dim", "8", '
     '"--noise-std", "0.05", "--batch-size", "64", "--dropout", "0.1", '
     '"--learning-rate", "0.001", "--seed", "42"], check=True)\n')
markdown('## 5. Put outputs into the training, artifacts and documentation folders\n'
         'The training folder contains only train/validation/test CSVs and the safe-column manifest. '
         'Weights and transforms go to preprocessing artifacts; plots and findings go to docs.')
runner=(ROOT/'pre-processing/run_pipeline.py').read_text()
tail=runner[runner.index("    for split in ('train','validation','test'):"):runner.index("\nif __name__")]
code('import shutil, json\nfigures = repo / "docs/figures"\nreports = repo / "docs/preprocessing"\n'
     'for path in (artifacts, figures, reports): path.mkdir(parents=True, exist_ok=True)\n'
     +textwrap.dedent(tail))
markdown('## 6. Output verification and model-ready rows\n'
         'Standard: 28 predictors. DAE: 16 predictors (8 latent + 7 categorical + reconstruction error). '
         'Six metadata/target fields are retained in addition. Use the manifest to select X and YIELD to select y.')
validation=json.loads((ROOT/'docs/preprocessing/output_validation.json').read_text())
code('subprocess.run([sys.executable, str(repo / "pre-processing/verify_outputs.py")], check=True)\n'
     'manifest = json.loads((dataset / "training/manifest.json").read_text())\n'
     'for arm in ("standard", "autoencoder"):\n'
     '    train = pd.read_csv(dataset / "training" / manifest[arm]["train"])\n'
     '    display(train.head())\n'
     '    print(arm, "rows:", len(train), "predictors:", len(manifest[arm]["predictor_columns"]))\n',
     [display({'application/json':validation,'text/plain':json.dumps(validation,indent=2)})])
markdown('## 7. Informative graphs and measured learning\n'
         'Coverage is unequal across states/seasons. Scaling changes units; DAE loss measures reconstruction. '
         'Best validation reconstruction MSE was 0.07724 at epoch 178, not a yield accuracy score. '
         'Autumn/Winter are unseen training categories and require separate evaluation.')
code('subprocess.run([sys.executable, str(repo / "pre-processing/make_figures.py")], check=True)')
captions=[
    ('01_observation_coverage.png','Observation coverage by state and season'),
    ('02_yield_distribution.png','Recorded yield distribution'),
    ('03_annual_yield_by_state.png','Recorded annual mean yield'),
    ('04_feature_correlation.png','Feature correlations: associations, not causes'),
    ('05_raw_vs_standardized_features.png','Raw inputs compared with standardized inputs'),
    ('06_autoencoder_reconstruction.png','Actual DAE reconstructions'),
    ('07_autoencoder_training_loss.png','Actual DAE training/validation history'),
]
for filename,caption in captions:
    markdown('### '+caption)
    encoded=base64.b64encode((ROOT/'docs/figures'/filename).read_bytes()).decode()
    code('from IPython.display import Image, display\n'
         'display(Image(filename=str(repo / "docs/figures/'+filename+'")))',
         [display({'image/png':encoded,'text/plain':caption})])
markdown('## 8. What is used for supervised training?\n'
         'Use DATASET/training/standard/train.csv or autoencoder/train.csv. '
         'Keep validation.csv and test.csv separate. Raw sources and rice_master.csv remain preserved. '
         'The fitted preprocessing DAE is not a fitted yield predictor.')
markdown('## 9. Standard and DAE representations\n'
         '| Property | Standard | DAE |\n|---|---|---|\n'
         '| Numerical representation | 21 scaled original columns | 8 learned latent columns |\n'
         '| Categories | 7 one-hot indicators | Same 7 indicators |\n'
         '| Extra score | None | Reconstruction MSE |\n'
         '| Predictor count | 28 | 16 |\n'
         '| Stored column count | 34 | 22 |\n\n'
         'Both versions use identical observations, yield labels and chronological splits. '
         'Standard preserves named features as a conventional reference. DAE tests learned compression. '
         'Compression can discard useful information, so fewer columns do not establish improved prediction. '
         'Gaussian noise is a training-only perturbation; exports use clean standardized inputs. '
         'State and season bypass the DAE. Latent coordinates have no fixed physical interpretation.')
markdown('### Why we use a Denoising Autoencoder\n'
         'The numerical inputs contain related measurements, including maximum, minimum and average '
         'temperature, rainfall, evaporation and derived water balance. A DAE can learn nonlinear '
         'combinations of these measurements and compress 21 values into eight latent coordinates.\n\n'
         'The bottleneck encourages a compact representation. Adding small Gaussian perturbations '
         '(standard deviation 0.05 after scaling) while targeting the original clean vector encourages '
         'stable input relationships rather than copying the disturbed measurements. Yield labels '
         'never enter this objective. The original observations are not changed and no new crop rows '
         'are created.\n\n'
         'We chose DAE as an experimental alternative to standard preprocessing. Compression may '
         'lose information relevant to yield. Low reconstruction error does not prove better yield '
         'prediction or removal of real measurement errors. Both representations therefore keep '
         'the same labels, rows and time splits. Reconstruction MSE is an auxiliary input, not '
         'a disease score or prediction uncertainty estimate.')
manifest=json.loads((ROOT/'DATASET/training/manifest.json').read_text(encoding='utf-8'))
for arm in ('standard','autoencoder'):
    markdown('### Exact '+arm+' predictor list\n'+ '\n'.join('- `'+name+'`' for name in manifest[arm]['predictor_columns']))
code('expected_numeric = '+repr([n.removeprefix('numeric__') for n in manifest['standard']['predictor_columns'] if n.startswith('numeric__')])+'\n'
     'assert manifest["standard"]["predictor_columns"] == ["numeric__" + n for n in expected_numeric] + '
     '[n for n in manifest["standard"]["predictor_columns"] if n.startswith("categorical__")]\n'
     'standard_categories = [n for n in manifest["standard"]["predictor_columns"] if n.startswith("categorical__")]\n'
     'assert manifest["autoencoder"]["predictor_columns"] == '
     '[f"AE_LATENT_{i:02d}" for i in range(1, 9)] + standard_categories + ["AE_RECONSTRUCTION_MSE"]\n'
     'assert len(standard_categories) == 7\n'
     'for arm, count in (("standard", 28), ("autoencoder", 16)):\n'
     '    assert len(manifest[arm]["predictor_columns"]) == count\n'
     '    for partition, expected_rows in (("train", 1485), ("validation", 245), ("test", 288)):\n'
     '        frame = pd.read_csv(dataset / "training" / manifest[arm][partition])\n'
     '        assert len(frame) == expected_rows\n'
     '        assert frame.shape[1] == count + 6\n'
     '        assert frame[manifest[arm]["predictor_columns"]].notna().all().all()\n'
     '        print(arm, partition, frame.shape)\n'
     'print("Feature schemas match the presentation.")\n')
notebook=dict(nbformat=4,nbformat_minor=5,metadata={'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'},
              'language_info':{'name':'python'},'colab':{'name':'Crop_Preprocessing.ipynb'}},cells=cells)
for index,cell in enumerate(cells): cell['id']=f'crop-cell-{index:02d}'
destination=ROOT/'pre-processing/Crop_Preprocessing.ipynb'
destination.write_text(json.dumps(notebook,indent=1),encoding='utf-8')
print(f'Created {destination}: {len(cells)} cells, seven saved figures, visible preprocessing code.')
