"""Prepare or explicitly train four tabular experiments. Default is check-only.

Run from the repository root. Raw data and preprocessing are never refitted.
Only manifest-declared predictors are used. Validation selects MLP epochs and
GBDT hyperparameters; test labels are used only after that selection.
"""
import argparse
import copy
import hashlib
import importlib.util
import json
import pickle
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load_data(root=ROOT):
    directory=root/'DATASET/training'
    manifest=json.loads((directory/'manifest.json').read_text())
    arms={}
    for arm in ('standard','autoencoder'):
        columns=manifest[arm]['predictor_columns']
        if len(set(columns))!=len(columns) or set(columns)&{'YIELD','FYEAR','DISTRICT','PRODUCTION_TONNES','IDREGION'}:
            raise ValueError('Duplicate or leaking predictors')
        partitions={}
        for split in ('train','validation','test'):
            path=directory/manifest[arm][split]
            frame=pd.read_csv(path)
            if len(frame)!=manifest['split_rows'][split]: raise ValueError(f'{arm}/{split} row count')
            bounds={'train':(2001,2015),'validation':(2016,2017),'test':(2018,2019)}[split]
            if not frame.FYEAR.between(*bounds).all(): raise ValueError('Incorrect chronological split')
            values=frame[columns].to_numpy(dtype=np.float32)
            labels=frame[manifest['target']].to_numpy(dtype=np.float32)
            if not np.isfinite(values).all() or not np.isfinite(labels).all(): raise ValueError('Nonfinite values')
            keys=frame[['IDREGION','FYEAR','SEASON']]
            if keys.duplicated().any(): raise ValueError('Duplicate observation')
            partitions[split]={'frame':frame,'x':values,'y':labels,'sha256':digest(path)}
        sets=[set(map(tuple,partitions[s]['frame'][['IDREGION','FYEAR','SEASON']].to_numpy())) for s in ('train','validation','test')]
        if any(sets[i]&sets[j] for i in range(3) for j in range(i)): raise ValueError('Split overlap')
        arms[arm]=partitions
    for split in ('train','validation','test'):
        a,b=arms['standard'][split],arms['autoencoder'][split]
        if not a['frame'][['IDREGION','FYEAR','SEASON']].equals(b['frame'][['IDREGION','FYEAR','SEASON']]) or not np.array_equal(a['y'],b['y']):
            raise ValueError('Representations are not aligned')
    return manifest,arms

def metrics(y,pred):
    from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
    return {'MAE':float(mean_absolute_error(y,pred)), 'RMSE':float(np.sqrt(mean_squared_error(y,pred))), 'R2':float(r2_score(y,pred))}

def fit_mlp(parts,epochs,seed):
    import torch
    from torch.utils.data import DataLoader, TensorDataset
    from APP.models.tabular import YieldMLP
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    model=YieldMLP(parts['train']['x'].shape[1])
    mean=float(parts['train']['y'].mean());scale=max(float(parts['train']['y'].std()),1e-6)
    loader=DataLoader(TensorDataset(torch.tensor(parts['train']['x']),torch.tensor((parts['train']['y']-mean)/scale)),batch_size=64,shuffle=True,generator=torch.Generator().manual_seed(seed))
    optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.0001)
    loss_fn=torch.nn.MSELoss();best=float('inf');best_state=None;best_epoch=0;stale=0;history=[]
    for epoch in range(1,epochs+1):
        model.train();total=0
        for x,y in loader:
            optimizer.zero_grad();loss=loss_fn(model(x),y);loss.backward();optimizer.step();total+=float(loss.detach())*len(x)
        model.eval()
        with torch.no_grad(): pred=model(torch.tensor(parts['validation']['x'])).numpy()*scale+mean
        score=metrics(parts['validation']['y'],pred)['RMSE']
        history.append({'epoch':epoch,'train_normalized_MSE':total/len(parts['train']['y']),'validation_RMSE':score})
        if score<best:
            best=score;best_epoch=epoch;best_state=copy.deepcopy(model.state_dict());stale=0
        else: stale+=1
        if stale>=30: break
    model.load_state_dict(best_state);model.eval()
    def predict(x):
        with torch.no_grad(): return model(torch.tensor(x)).numpy()*scale+mean
    return model,predict,{'target_mean':mean,'target_scale':scale,'best_epoch':best_epoch},history

def fit_gbdt(parts,seed):
    from APP.models.tabular import make_gbdt
    best=None;best_score=float('inf');best_config=None;history=[]
    for leaves,lr,iterations in [(7,.05,200),(15,.05,200),(15,.03,300)]:
        model=make_gbdt(seed);model.set_params(max_leaf_nodes=leaves,learning_rate=lr,max_iter=iterations)
        model.fit(parts['train']['x'],parts['train']['y'])
        score=metrics(parts['validation']['y'],model.predict(parts['validation']['x']))['RMSE']
        config={'max_leaf_nodes':leaves,'learning_rate':lr,'max_iter':iterations}
        history.append({**config,'validation_RMSE':score})
        if score<best_score: best,best_score,best_config=model,score,config
    return best,best.predict,best_config,history

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train',action='store_true',help='Explicitly authorize fitting; omitted means readiness checks only')
    parser.add_argument('--epochs',type=int,default=250)
    parser.add_argument('--seed',type=int,default=42)
    parser.add_argument('--output',type=Path,help='New output directory; must not already exist')
    args=parser.parse_args()
    if args.epochs<1: parser.error('epochs must be positive')
    manifest,arms=load_data()
    readiness={'status':'data_ready_for_tabular_training','trained':False,'target':manifest['target'],'units':'tonnes/hectare',
               'missing_training_dependencies':[name for name in ('torch','sklearn') if importlib.util.find_spec(name) is None],
               'splits':manifest['split_rows'],'experiments':['standard_mlp','standard_gbdt','autoencoder_mlp','autoencoder_gbdt'],
               'predictors':{arm:len(manifest[arm]['predictor_columns']) for arm in arms},
               'input_sha256':{arm:{s:p['sha256'] for s,p in parts.items()} for arm,parts in arms.items()},
               'limitations':['District-scale data, not farm-scale validation','Retrospective full-season weather','Unseen Autumn/Winter categories','Sequence models not prepared by this runner']}
    if not args.train:
        print(json.dumps(readiness,indent=2));return
    import torch
    torch.set_num_threads(1)
    output=args.output or ROOT/'APP/training/runs'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
    output.mkdir(parents=True,exist_ok=False)
    results=[]
    for arm,parts in arms.items():
        for kind in ('mlp','gbdt'):
            model,predict,configuration,history=fit_mlp(parts,args.epochs,args.seed) if kind=='mlp' else fit_gbdt(parts,args.seed)
            folder=output/f'{arm}_{kind}';folder.mkdir()
            bundle={'representation':arm,'model_kind':kind,'predictor_columns':manifest[arm]['predictor_columns'],
                    'target':'YIELD','units':'tonnes/hectare','seed':args.seed,'configuration':configuration,
                    'training_data_sha256':parts['train']['sha256'], 'preprocessing_manifest_sha256':digest(ROOT/'DATASET/training/manifest.json'),
                    'preprocessing_artifact_sha256':{name:digest(ROOT/'pre-processing/artifacts'/name) for name in (['standard_preprocessor.pkl'] if arm=='standard' else ['standard_preprocessor.pkl','denoising_autoencoder.pt'])}}
            if kind=='mlp': torch.save({'state_dict':model.state_dict(),**bundle},folder/'model.pt')
            else:
                with (folder/'model.pkl').open('wb') as handle: pickle.dump(model,handle)
            measured={s:metrics(p['y'],predict(p['x'])) for s,p in parts.items()}
            # Save residuals and grouped diagnostics only after validation selects the model.
            test=parts['test']['frame'][manifest['metadata_columns']+['YIELD']].copy()
            test['PREDICTED_YIELD']=predict(parts['test']['x']);test['RESIDUAL']=test.YIELD-test.PREDICTED_YIELD
            test.to_csv(folder/'test_predictions.csv',index=False)
            groups={column:{str(value):metrics(group.YIELD,group.PREDICTED_YIELD) for value,group in test.groupby(column) if len(group)>=2} for column in ('STATE','SEASON')}
            bundle.update({'metrics':measured,'test_breakdowns':groups,'history':history})
            (folder/'bundle.json').write_text(json.dumps(bundle,indent=2),encoding='utf-8')
            results.append({'experiment':f'{arm}_{kind}',**measured})
    winner=min(results,key=lambda item:item['validation']['RMSE'])['experiment']
    # A constant baseline is fitted from training labels only, not held-out labels.
    baseline={arm:{s:metrics(p['y'],np.full(len(p['y']),parts['train']['y'].mean())) for s,p in parts.items()} for arm,parts in arms.items()}
    (output/'comparison.json').write_text(json.dumps({'results':results,'training_mean_baseline':baseline,'selected_by_validation_RMSE':winner,'selection_rule':'Never rank models by test scores','readiness':readiness},indent=2),encoding='utf-8')
    print(f'Completed experiments in {output}. Selected by validation: {winner}. No app deployment or model activation performed.')

if __name__=='__main__': main()
