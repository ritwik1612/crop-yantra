"""Evaluate fixed trained models and create a reproducible private demo-photo pack.

No fitting, threshold tuning, checkpoint selection, app activation or source edits.
"""
import argparse
import hashlib
import io
import json
import math
import pickle
import random
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
import torch
from sklearn.inspection import permutation_importance
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from threadpoolctl import threadpool_limits
from torchvision.models import EfficientNet_B0_Weights, efficientnet_b0

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from APP.training.train import load_data, metrics
from APP.inference.preprocess import transform_rows


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def regression_metrics(y, pred):
    result = metrics(y, pred)
    if len(y) < 2 or np.ptp(y) == 0:
        result['R2'] = None
    return {'rows': len(y), **result, 'mean_bias_t_ha': float(np.mean(pred-y)),
            'within_0_5_t_ha_pct': float(np.mean(np.abs(y-pred) <= .5)*100),
            'within_1_t_ha_pct': float(np.mean(np.abs(y-pred) <= 1)*100)}


def groups(frame, column):
    return {str(value): regression_metrics(part.YIELD.to_numpy(), part.PREDICTED_YIELD.to_numpy())
            for value, part in frame.groupby(column, observed=True)}


def evaluate_yield(run, output):
    comparison = json.loads((run/'comparison.json').read_text())
    selected = comparison['selected_by_validation_RMSE']
    folder = run/selected
    info = json.loads((folder/'bundle.json').read_text())
    if info['model_kind'] != 'gbdt':
        raise ValueError('This audit expects the recorded validation-selected tree winner')
    manifest, arms = load_data()
    parts = arms[info['representation']]
    for name, expected in info['preprocessing_artifact_sha256'].items():
        if digest(ROOT/'pre-processing/artifacts'/name) != expected:
            raise ValueError('Preprocessing artifact changed after training')
    if digest(ROOT/'DATASET/training/manifest.json') != info['preprocessing_manifest_sha256']:
        raise ValueError('Training manifest changed after fitting')
    if parts['train']['sha256'] != info['training_data_sha256']:
        raise ValueError('Training input hash changed')
    with (folder/'model.pkl').open('rb') as stream:
        model = pickle.load(stream)
    test = parts['test']['frame'].copy()
    test['PREDICTED_YIELD'] = model.predict(parts['test']['x'])
    measured = regression_metrics(test.YIELD.to_numpy(), test.PREDICTED_YIELD.to_numpy())
    if not np.isclose(measured['MAE'], info['metrics']['test']['MAE'], atol=1e-8):
        raise ValueError('Saved yield evaluation could not be reproduced')
    master = pd.read_csv(ROOT/'DATASET/merged/rice_master.csv')
    keys = ['IDREGION', 'FYEAR', 'SEASON']
    raw = master.set_index(keys).loc[pd.MultiIndex.from_frame(test[keys])].reset_index()
    reproduced, _ = transform_rows(raw.to_dict('records'), info['representation'])
    if not np.allclose(reproduced.to_numpy(), parts['test']['x'], atol=1e-5, rtol=1e-5):
        raise ValueError('Full-feature inference does not reproduce training representation')
    test['rainfall_band'] = pd.qcut(raw.PREC_TOTAL, 4, labels=['Q1 lowest','Q2','Q3','Q4 highest'], duplicates='raise').to_numpy()
    test['temperature_band'] = pd.qcut(raw.TAVG_MEAN, 4, labels=['Q1 coolest','Q2','Q3','Q4 warmest'], duplicates='raise').to_numpy()
    test['RESIDUAL'] = test.YIELD-test.PREDICTED_YIELD
    test['ABS_ERROR'] = test.RESIDUAL.abs()
    test['heldout_row'] = np.arange(len(test))
    importance = permutation_importance(model, parts['validation']['x'], parts['validation']['y'],
        scoring='neg_mean_absolute_error', n_repeats=5, random_state=42, n_jobs=1)
    feature_importance = sorted([{'feature': name, 'validation_MAE_increase': float(mean),
        'repeat_std': float(std)} for name, mean, std in zip(info['predictor_columns'], importance.importances_mean,
        importance.importances_std)], key=lambda row: row['validation_MAE_increase'], reverse=True)
    baseline = float(parts['train']['y'].mean())
    baseline_result = regression_metrics(test.YIELD.to_numpy(), np.full(len(test), baseline))
    weather_names = ['TMAX_MEAN','TMIN_MEAN','TAVG_MEAN','PREC_TOTAL','RAD_TOTAL','RELH_MEAN','WSPD_MEAN']
    missing = raw.copy()
    missing[weather_names] = np.nan
    transformed, _ = transform_rows(missing.to_dict('records'), info['representation'])
    missing_prediction = model.predict(transformed.to_numpy(dtype=np.float32))
    missing_metrics = regression_metrics(test.YIELD.to_numpy(), missing_prediction)
    rng = np.random.default_rng(42)
    errors = test.ABS_ERROR.to_numpy()
    boot = np.mean(errors[rng.integers(0, len(errors), size=(2000,len(errors)))], axis=1)
    report = {'selected_experiment': selected, 'selection_basis': 'Saved validation RMSE; not reselected on test',
        'model_sha256': digest(folder/'model.pkl'), 'overall_test': measured,
        'test_MAE_bootstrap_95_interval': np.quantile(boot, [.025,.975]).tolist(),
        'bootstrap_limit': 'Row bootstrap only; related districts/years violate full independence, so interval is descriptive',
        'training_mean_baseline': baseline_result,
        'baseline_MAE_reduction_pct': (1-measured['MAE']/baseline_result['MAE'])*100,
        'by_state': groups(test,'STATE'), 'by_season': groups(test,'SEASON'),
        'by_year': groups(test,'FYEAR'), 'by_rainfall_quartile': groups(test,'rainfall_band'),
        'by_temperature_quartile': groups(test,'temperature_band'),
        'missing_weather_stress': {'fields_masked': weather_names, 'metrics': missing_metrics,
            'note': 'Artificial feature-masking stress, not a new measured weather/yield dataset; derived weather features remain available'},
        'validation_permutation_importance': feature_importance,
        'original_four_experiments': comparison['results'],
        'representative_test_cases': test.sort_values(['STATE','SEASON','FYEAR','DISTRICT']).groupby(['STATE','SEASON'],observed=True).head(1)[keys+['STATE','DISTRICT','YIELD','PREDICTED_YIELD','ABS_ERROR']].to_dict('records'),
        'largest_errors': test.nlargest(10,'ABS_ERROR')[['STATE','DISTRICT','FYEAR','SEASON','YIELD','PREDICTED_YIELD','ABS_ERROR']].to_dict('records')}
    fig, axes = plt.subplots(1,2,figsize=(12,4.5),layout='constrained')
    axes[0].scatter(test.YIELD,test.PREDICTED_YIELD,s=20,alpha=.6,color='#285b46')
    limits=[min(test.YIELD.min(),test.PREDICTED_YIELD.min()),max(test.YIELD.max(),test.PREDICTED_YIELD.max())]
    axes[0].plot(limits,limits,'--',color='#888');axes[0].set(xlabel='Observed yield (t/ha)',ylabel='Predicted yield (t/ha)',title='Held-out yield observations (n=288)')
    state=report['by_state'];axes[1].barh(list(state),[r['MAE'] for r in state.values()],color='#59774f')
    axes[1].set(xlabel='Mean absolute error (t/ha)',title='Yield error by state')
    fig.savefig(output/'yield_evaluation.png',dpi=160);plt.close(fig)
    return report


def classify(model, records, directory, transform, alteration=None):
    probabilities=[]
    with torch.inference_mode():
        for start in range(0,len(records),32):
            tensors=[]
            for row in records[start:start+32]:
                with Image.open(directory/row['path']) as source:
                    image=ImageOps.exif_transpose(source).convert('RGB')
                    if alteration:image=alteration(image)
                    tensors.append(transform(image))
            probabilities.extend(torch.softmax(model(torch.stack(tensors)),dim=1).cpu().tolist())
            print(f'  Scored {min(start+32,len(records))}/{len(records)} photos',flush=True)
    return np.array(probabilities)


def image_metrics(actual, probabilities):
    predicted=probabilities.argmax(1)
    return {'photos': len(actual), 'accuracy':float(accuracy_score(actual,predicted)),
            'macro_F1':float(f1_score(actual,predicted,labels=list(range(4)),average='macro',zero_division=0))}


def evaluate_images(run, output):
    directory=ROOT/'DATASET/images/prepared/paddy_doctor_4class'
    manifest=json.loads((directory/'manifest.json').read_text())
    checkpoint=torch.load(run/'model.pt',map_location='cpu',weights_only=True)
    if checkpoint['manifest_sha256']!=digest(directory/'manifest.json') or checkpoint['classes']!=manifest['classes']:
        raise ValueError('Image model and dataset manifest disagree')
    classes=checkpoint['classes'];records=[row for row in manifest['images'] if row['split']=='test']
    for row in records:
        if digest(directory/row['path'])!=row['sha256']:raise ValueError('Test image hash mismatch')
    model=efficientnet_b0(weights=None);model.classifier[-1]=torch.nn.Linear(model.classifier[-1].in_features,4)
    model.load_state_dict(checkpoint['state_dict'],strict=True);model.eval()
    transform=EfficientNet_B0_Weights.IMAGENET1K_V1.transforms()
    print('Image test: original photos',flush=True)
    base=classify(model,records,directory,transform)
    actual=np.array([row['class_index'] for row in records]);predicted=base.argmax(1)
    measured=image_metrics(actual,base)
    prior=json.loads((run/'metrics.json').read_text())
    if not np.isclose(measured['accuracy'],prior['test']['accuracy'],atol=1e-10):
        raise ValueError('Saved image evaluation could not be reproduced')
    def compressed(image):
        stream=io.BytesIO();image.save(stream,format='JPEG',quality=35);stream.seek(0)
        with Image.open(stream) as read:return read.convert('RGB').copy()
    alterations={'darker_65pct':lambda image:ImageEnhance.Brightness(image).enhance(.65),
        'brighter_135pct':lambda image:ImageEnhance.Brightness(image).enhance(1.35),
        'blur_radius_2':lambda image:image.filter(ImageFilter.GaussianBlur(2)),
        'jpeg_quality_35':compressed}
    conditions={'original':measured}
    for name, alteration in alterations.items():
        print(f'Image stress: {name}',flush=True)
        probabilities=classify(model,records,directory,transform,alteration)
        conditions[name]={**image_metrics(actual,probabilities),
            'changed_labels_vs_original':int(np.sum(probabilities.argmax(1)!=predicted))}
    per_image=[]
    for row,p,guess in zip(records,base,predicted):
        per_image.append({'image_id':row['image_id'],'source_path':row['path'],'true_class':row['class'],
            'predicted_class':classes[int(guess)],'correct':bool(guess==row['class_index']),
            'top_softmax_score':float(p.max()),'age_days':row.get('age_days'), 'variety':row.get('variety'),
            'group_id':row['group_id'],'sha256':row['sha256']})
    frame=pd.DataFrame(per_image)
    age=pd.to_numeric(frame.age_days,errors='coerce')
    frame['age_band']=pd.cut(age,[-np.inf,30,60,90,np.inf],right=False,labels=['under 30 days','30–59 days','60–89 days','90+ days']).astype('str')
    strata={field:{str(key):{'photos':len(part),'correct':int(part.correct.sum()),'accuracy':float(part.correct.mean())}
        for key,part in frame.groupby(field,dropna=False)} for field in ['age_band','variety']}
    n=len(actual);p=measured['accuracy'];z=1.96;denominator=1+z*z/n
    centre=(p+z*z/(2*n))/denominator;half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denominator
    diagnostics=[]
    rng=np.random.default_rng(42)
    for name,image in [('blank_white',Image.new('RGB',(480,640),'white')),
                       ('blank_black',Image.new('RGB',(480,640),'black')),
                       ('random_noise',Image.fromarray(rng.integers(0,256,(640,480,3),dtype=np.uint8)))]:
        with torch.inference_mode():prob=torch.softmax(model(transform(image).unsqueeze(0)),dim=1)[0].numpy()
        diagnostics.append({'input':name,'predicted_class':classes[int(prob.argmax())],
                            'top_softmax_score':float(prob.max()),'ground_truth_rice_class':None})
    matrix=confusion_matrix(actual,predicted,labels=list(range(4)))
    fig,axes=plt.subplots(1,2,figsize=(12.5,4.8),layout='constrained')
    axes[0].imshow(matrix,cmap='Greens',vmin=0,vmax=60)
    labels=['Bacterial blight','Blast','Brown spot','Healthy']
    axes[0].set(xticks=range(4),yticks=range(4),xticklabels=labels,yticklabels=labels,xlabel='Predicted',ylabel='True class',title='Original test photos (n=240)')
    axes[0].tick_params(axis='x',rotation=30)
    for i in range(4):
        for j in range(4):axes[0].text(j,i,str(matrix[i,j]),ha='center',va='center',color='white' if matrix[i,j]>35 else 'black')
    names=list(conditions);axes[1].barh(names,[conditions[k]['accuracy']*100 for k in names],color='#59774f')
    axes[1].set(xlim=(0,100),xlabel='Accuracy (%)',title='Same test photos under fixed perturbations')
    fig.savefig(output/'image_evaluation.png',dpi=160);plt.close(fig)
    return {'model_sha256':digest(run/'model.pt'),'overall_test':measured,
        'accuracy_Wilson_95_interval':[centre-half,centre+half],
        'interval_limit':'Binomial interval assumes independent photos; capture-session independence is not established',
        'classification_report':classification_report(actual,predicted,labels=list(range(4)),target_names=classes,output_dict=True,zero_division=0),
        'confusion_matrix':matrix.tolist(),'conditions':conditions,'by_metadata':strata,
        'non_rice_diagnostics':diagnostics,'per_image':per_image,
        'limitations':['No reliable season, district or capture-session labels in the photo release',
            'No independent external field-photo test performed','Class scores are uncalibrated and do not validate unsupported-input rejection',
            'Perturbations reuse the same photos, not additional independent test samples']}, records


def make_demo(image_report, destination, directory, replace_generated=False):
    destination=destination.resolve();directory=directory.resolve()
    previous=[]
    if destination.exists():
        if not replace_generated:raise FileExistsError('Demo folder already exists')
        previous=json.loads((destination/'demo_manifest.json').read_text(encoding='utf8'))
        for row in previous:
            path=(destination/row['demo_path']).resolve()
            if not path.is_relative_to(destination.resolve()) or digest(path)!=row['sha256']:
                raise ValueError('A previous demo copy was edited; refusing to replace it')
    else:destination.mkdir(parents=True,exist_ok=False)
    rows=image_report['per_image'];chosen=[]
    # Selection is independent of correctness: fixed seeded random sample within each true class.
    for label in sorted({row['true_class'] for row in rows}):
        candidates=sorted([r for r in rows if r['true_class']==label],key=lambda r:r['image_id'])
        ordinary=random.Random(42).sample(candidates,8)
        ordinary_ids={row['image_id'] for row in ordinary}
        for i,row in enumerate(ordinary,1):
            chosen.append((label,f'{i:02d}_{row["image_id"]}',row,'seeded_class_sample'))
        failures=sorted([r for r in candidates if not r['correct'] and r['image_id'] not in ordinary_ids],key=lambda r:r['image_id'])[:2]
        for i,row in enumerate(failures,1):
            chosen.append((f'known_misclassifications/{label}',f'{i:02d}_{row["image_id"]}',row,'known_failure_example'))
    manifest=[]
    for folder,name,row,selection in chosen:
        path=destination/folder/name;path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(directory/row['source_path'],path)
        if digest(path)!=row['sha256']:raise ValueError('Demo copy differs from source')
        manifest.append({'demo_path':path.relative_to(destination).as_posix(),'selection':selection,
            'source_split':'test',**row,'season':None})
    retained={row['demo_path'] for row in manifest}
    for old in previous:
        if old['demo_path'] not in retained:
            # Only an unchanged generated copy checked above can be removed.
            # Its source photo remains preserved in the prepared dataset.
            (destination/old['demo_path']).unlink()
    (destination/'demo_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    lines=['# Rice-photo demo pack','',
        'Original held-out Paddy Doctor photos, copied without changing training data or weights.',
        'Use the four disease/healthy folders for ordinary examples. Each contains eight seeded random photos, not eight guaranteed successes.',
        'The known_misclassifications folders show two real failures per class so you can demonstrate limitations.',
        'No reliable season labels are supplied. Photos are therefore grouped by disease, not assigned invented Kharif/Rabi labels.',
        'These are known test-set examples, not a new independent evaluation dataset. Do not retrain on them while retaining the reported test score.',
        'The public web app may still be a preview; possessing these photos does not connect trained inference.',
        'Source: https://www.kaggle.com/competitions/paddy-disease-classification/data . Keep photos private and follow source terms.','',
        '| Demo photo | True class | Current model prediction | Correct? |','|---|---|---|---|']
    lines += [f'| {r["demo_path"]} | {r["true_class"]} | {r["predicted_class"]} | {"Yes" if r["correct"] else "No"} |' for r in manifest]
    (destination/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
    return {'path':str(destination.relative_to(ROOT)),'photos':len(manifest),
        'unique_source_photos':len({row['image_id'] for row in manifest}),
        'ordinary_examples':sum(r['selection']=='seeded_class_sample' for r in manifest),
        'known_failure_examples':sum(r['selection']=='known_failure_example' for r in manifest),
        'bytes':sum(path.stat().st_size for path in destination.rglob('*') if path.is_file())}


def md_table(headers, rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+
        ['| '+' | '.join(str(value) for value in row)+' |' for row in rows])


def write_report(report, output):
    y=report['yield'];im=report['images'];m=y['overall_test'];a=im['overall_test']
    sections=['# Crop Yantra model evaluation','',
        f'Fixed saved models evaluated at {report["evaluated_utc"]}. No retraining, threshold adjustment or checkpoint reselection.',
        '', '## Summary','',f'- Yield winner: **{y["selected_experiment"]}**, selected by the original validation RMSE.',
        f'- Yield test MAE: **{m["MAE"]:.3f} t/ha**; RMSE **{m["RMSE"]:.3f} t/ha**; R² **{m["R2"]:.3f}** across {m["rows"]} observations.',
        f'- Within ±0.5 t/ha: **{m["within_0_5_t_ha_pct"]:.1f}%**; within ±1 t/ha: **{m["within_1_t_ha_pct"]:.1f}%**.',
        f'- Image test accuracy: **{a["accuracy"]*100:.2f}%**, macro-F1 **{a["macro_F1"]:.3f}**, across {a["photos"]} photos.',
        '- Suitable for a limited academic prototype. These results do not establish farm-level yield forecasts or reliable field diagnosis.',
        '', '## Practical verdict','',
        f'The yield model is moderately useful on this historical hold-out, not uniformly reliable across regions. It underestimates by {abs(m["mean_bias_t_ha"]):.3f} t/ha on average. Only {m["within_0_5_t_ha_pct"]:.1f}% of cases fall within ±0.5 t/ha, despite {m["within_1_t_ha_pct"]:.1f}% falling within ±1 t/ha.',
        'Karnataka has the smallest observed state MAE. Telangana has the largest, with a strong negative bias. Tamil Nadu and Telangana have negative subgroup R²: the model is worse than each subgroup’s own constant-mean reference on these rows. That diagnostic mean uses held-out outcomes and is not a deployable baseline.',
        'Rabi has the smallest seasonal MAE in this test. Autumn and Winter were absent from fitted season categories; those inputs encode as all-zero indicators. Their results must be presented with that limitation, not treated as equally supported seasons.',
        'The image model is adequate for a constrained four-class demonstration using clear rice-leaf photos. It is not a general crop detector. Blurred and bright images are more difficult; unsupported inputs still receive forced labels. Do not present class scores as verified confidence.',
        '', '## Yield across different inputs','',
        f'Training-mean baseline MAE is {y["training_mean_baseline"]["MAE"]:.3f} t/ha. The selected model reduces it by {y["baseline_MAE_reduction_pct"]:.1f}%. R² is not percentage accuracy. DAE did not improve the saved comparison.',
        '', '![Yield evaluation](yield_evaluation.png)']
    for key,title in [('by_state','State'),('by_season','Season'),('by_year','Crop year'),('by_rainfall_quartile','Rainfall quartile'),('by_temperature_quartile','Temperature quartile')]:
        sections += ['',f'### {title}','',md_table([title,'Rows','MAE (t/ha)','RMSE (t/ha)','R²','Mean bias (t/ha)'],
            [[name,v['rows'],f'{v["MAE"]:.3f}',f'{v["RMSE"]:.3f}','n/a' if v['R2'] is None else f'{v["R2"]:.3f}',f'{v["mean_bias_t_ha"]:.3f}'] for name,v in y[key].items()])]
    sections += ['','Small groups are descriptive only. Quartiles are defined on this held-out sample for diagnostic grouping, not new training features.',
        '', '### Input-masking stress','',f'Masking seven direct weather inputs and reusing training-median imputation gives MAE {y["missing_weather_stress"]["metrics"]["MAE"]:.3f} t/ha. This artificial stress leaves derived weather features available and is not a no-weather model or new measured yield scenario.',
        '', '### Most influential inputs (global validation diagnostic)','',
        md_table(['Predictor','Validation MAE increase when shuffled (t/ha)','Repeat std.'],[[r['feature'],f'{r["validation_MAE_increase"]:.4f}',f'{r["repeat_std"]:.4f}'] for r in y['validation_permutation_importance'][:10]]),
        '', 'Five seeded permutations on validation data. Correlated inputs can share or hide importance. This is neither causation nor a local explanation of one prediction.',
        'State indicators and latitude rank prominently alongside radiation and crop area. This suggests the model relies on regional patterns as well as weather; it does not establish transfer to unseen districts or states. Slightly better error under masking is not evidence to remove weather inputs: this exploratory stress leaves related derived variables intact and must not drive test-set tuning.',
        '', '### Representative held-out predictions','',md_table(['State','District','Year','Season','Observed t/ha','Predicted t/ha','Absolute error'],
            [[r['STATE'],r['DISTRICT'],r['FYEAR'],r['SEASON'],f'{r["YIELD"]:.3f}',f'{r["PREDICTED_YIELD"]:.3f}',f'{r["ABS_ERROR"]:.3f}'] for r in y['representative_test_cases']]),
        '', '### Ten largest yield errors','',md_table(['State','District','Year','Season','Observed t/ha','Predicted t/ha','Absolute error'],
            [[r['STATE'],r['DISTRICT'],r['FYEAR'],r['SEASON'],f'{r["YIELD"]:.3f}',f'{r["PREDICTED_YIELD"]:.3f}',f'{r["ABS_ERROR"]:.3f}'] for r in y['largest_errors']]),
        '', '## Image classification across different inputs','', '![Image evaluation](image_evaluation.png)','',
        md_table(['Class','Test photos','Precision','Recall','F1'],[[name,int(v['support']),f'{v["precision"]:.3f}',f'{v["recall"]:.3f}',f'{v["f1-score"]:.3f}'] for name,v in im['classification_report'].items() if name in ['bacterial_leaf_blight','blast','brown_spot','normal']]),
        '', 'Bacterial leaf blight has the lowest recall (49/60 detected correctly); brown spot has the highest (54/60). Healthy-leaf recall is 51/60, so nine healthy photos were assigned a disease label.',
        '', '### Fixed photo-quality stresses','',md_table(['Input condition','Photos','Accuracy','Macro-F1','Changed labels'],[[name,v['photos'],f'{100*v["accuracy"]:.2f}%',f'{v["macro_F1"]:.3f}',v.get('changed_labels_vs_original',0)] for name,v in im['conditions'].items()]),
        '', 'Perturbations are applied in memory before the same evaluation resize/crop/normalization. They reuse all 240 test photos, so they are not additional independent observations. No settings were tuned against these results.']
    for field,title in [('age_band','Source age'),('variety','Source variety')]:
        sections += ['',f'### {title}','',md_table([title,'Photos','Correct','Accuracy'],[[name,v['photos'],v['correct'],f'{100*v["accuracy"]:.1f}%'] for name,v in im['by_metadata'][field].items()])]
    sections += ['', 'Variety groups are highly uneven (189 of 240 test photos are ADT45). A 100% result on one or two photos does not establish cultivar reliability. The age bins are metadata groups, not season labels.',
        '', '### Unsupported-input diagnostic','',md_table(['Non-rice input','Forced model label','Top softmax score'],[[r['input'],r['predicted_class'],f'{100*r["top_softmax_score"]:.1f}%'] for r in im['non_rice_diagnostics']]),
        '', 'Blank/noise inputs have no true rice class. A forced label is a failure of unsupported-input handling, not a valid diagnosis; a high score is not proof of correctness. No abstention threshold was tuned.',
        '', '## Demo image folder','',f'{report["demo"]["ordinary_examples"]} seeded ordinary examples and {report["demo"]["known_failure_examples"]} explicitly identified failure examples were copied into the requested demo folder. See its README for true labels and current predictions. Grouping uses disease class because no reliable season/district labels exist.',
        '', '## Limits and interpretation','',
        '- Both hold-outs come from the existing source, not an external field validation. Perceptual deduplication does not establish independent plant/capture sessions.',
        '- Yield data is district-scale, related across years, and uses full-season weather. It does not validate current-year early forecasting, unseen districts or farm-scale estimates.',
        '- Once examples are used in demos or further model choices, they are no longer a fresh independent test. Do not improve a model on these errors and reuse the same score as unbiased new evidence.',
        '- Photos support four rice classes only. They have no paired yield-loss labels, calibrated confidence, validated unknown-crop rejection or reliable season metadata.',
        '- The public app was not connected to these models by this evaluation. Its preview output must not be presented as trained inference.',
        '', 'Source collection: [Paddy Doctor competition](https://www.kaggle.com/competitions/paddy-disease-classification/data). All copied photos retain source rights and stay local.',
        '', 'Detailed machine-readable metrics, model hashes and per-photo results are in evaluation.json. Original training artifacts and datasets are unchanged.']
    (output/'Evaluation.md').write_text('\n'.join(sections)+'\n',encoding='utf8')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--yield-run',type=Path,default=ROOT/'APP/training/runs/20261017T175142_753017Z')
    parser.add_argument('--image-run',type=Path,default=ROOT/'APP/training/runs/images_20261017T175203_027881Z')
    parser.add_argument('--output',type=Path,default=ROOT/'docs/evaluation/2026-10-17')
    parser.add_argument('--demo-dir',type=Path,default=ROOT/'Testing Images')
    args=parser.parse_args()
    if args.output.exists() or args.demo_dir.exists():raise FileExistsError('Use new output/demo directories to preserve prior audits')
    args.output.mkdir(parents=True)
    torch.set_num_threads(2)
    with threadpool_limits(limits=2):
        print('Evaluating fixed yield model...',flush=True)
        y=evaluate_yield(args.yield_run,args.output)
        print('Evaluating fixed rice-image classifier...',flush=True)
        im,_=evaluate_images(args.image_run,args.output)
        demo=make_demo(im,args.demo_dir,ROOT/'DATASET/images/prepared/paddy_doctor_4class')
    if y['model_sha256']!=digest(args.yield_run/y['selected_experiment']/'model.pkl') or im['model_sha256']!=digest(args.image_run/'model.pt'):
        raise ValueError('Model weights changed during evaluation')
    report={'evaluated_utc':datetime.now(timezone.utc).isoformat(),'seed':42,'no_retraining':True,
        'yield_run':str(args.yield_run.relative_to(ROOT)),'image_run':str(args.image_run.relative_to(ROOT)),
        'yield':y,'images':im,'demo':demo}
    (args.output/'evaluation.json').write_text(json.dumps(report,indent=2,allow_nan=False)+'\n',encoding='utf8')
    write_report(report,args.output)
    print(json.dumps({'report':str(args.output/'Evaluation.md'),'yield_test':y['overall_test'],
        'image_conditions':im['conditions'],'demo':demo},indent=2))


if __name__=='__main__':main()
