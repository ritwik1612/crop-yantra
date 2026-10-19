"""Train a recent-data candidate without overwriting the installed model.

Predeclared chronological split: train <=2020, validation 2021-22, test 2023-24.
Select neural hyperparameters/epochs by validation only, then evaluate test once.
"""
import copy
import hashlib
import json
import pickle
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.ensemble import HistGradientBoostingRegressor
from torch.utils.data import DataLoader, TensorDataset

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'pre-processing'))
from denoising_autoencoder import select_numeric_features, METADATA_COLUMNS
from APP.models.contextual_yield import ContextualYield
from APP.training.train import metrics


def main():
    torch.set_num_threads(1)
    run=ROOT/'APP/training/runs/recent_yield_20261019'
    run.mkdir(exist_ok=True)
    if (run/'model.pt').exists():raise ValueError('Completed candidate already exists; do not overwrite')
    data=pd.read_csv(ROOT/'DATASET/candidates/recent_yield/rice_master.csv')
    numeric=select_numeric_features(data)
    frames={'train':data[data.FYEAR<=2020].copy(), 'validation':data[data.FYEAR.between(2021,2022)].copy(),
            'test':data[data.FYEAR.between(2023,2024)].copy()}
    if any(len(f)<100 for f in frames.values()):raise ValueError('Insufficient temporal evaluation rows')
    processor=ColumnTransformer([
        ('numeric',Pipeline([('imputer',SimpleImputer(strategy='median')),('scaler',StandardScaler())]),numeric),
        ('categorical',OneHotEncoder(handle_unknown='ignore',sparse_output=False),['STATE','SEASON'])])
    processor.fit(frames['train'][numeric+['STATE','SEASON']])
    names=processor.get_feature_names_out().tolist()
    input_count=len(names)
    train=frames['train'];vocab={k:i+1 for i,k in enumerate(sorted((train.STATE+'|'+train.DISTRICT+'|'+train.SEASON).unique()))}
    year_mean=float(train.FYEAR.mean());year_scale=float(train.FYEAR.std(ddof=0))
    target_mean=float(train.YIELD.mean());target_scale=float(train.YIELD.std(ddof=0))
    x={s:processor.transform(f[numeric+['STATE','SEASON']]).astype(np.float32) for s,f in frames.items()}
    arrays={s:torch.tensor(np.column_stack([x[s],(f.FYEAR-year_mean)/year_scale,
            (f.STATE+'|'+f.DISTRICT+'|'+f.SEASON).map(vocab).fillna(0)]).astype(np.float32)) for s,f in frames.items()}
    y=torch.tensor((train.YIELD.to_numpy(np.float32)-target_mean)/target_scale)
    directory=ROOT/'DATASET/training/recent/standard';directory.mkdir(parents=True,exist_ok=True)
    for split,f in frames.items():
        pd.concat([f[METADATA_COLUMNS].reset_index(drop=True),pd.DataFrame(x[split],columns=names)],axis=1).to_csv(directory/f'{split}.csv',index=False)
    with (run/'preprocessor.pkl').open('wb') as handle:pickle.dump(processor,handle)
    history=[];candidates=[]
    for lr,decay,dropout,use_year in [(lr,decay,dropout,trend) for trend in (False,True)
                                    for lr,decay,dropout in [(.001,.01,.35),(.0003,.01,.35),(.001,.1,.5)]]:
        for seed in (42,73,101):
            torch.manual_seed(seed);model=ContextualYield(len(vocab),dropout,input_count)
            active_arrays={s:v.clone() for s,v in arrays.items()}
            if not use_year:
                for v in active_arrays.values():v[:,input_count]=0
                model.trend.weight.requires_grad_(False)
            with torch.no_grad():model.weather.network[-1].weight.zero_();model.weather.network[-1].bias.zero_()
            warm=torch.optim.AdamW(list(model.district.parameters())+list(model.trend.parameters()),lr=.03,weight_decay=.1)
            for _ in range(500):
                warm.zero_grad(set_to_none=True)
                pred=model.district(active_arrays['train'][:,input_count+1].long()).squeeze(-1)+model.trend(active_arrays['train'][:,input_count:input_count+1]).squeeze(-1)
                loss=torch.nn.functional.mse_loss(pred,y);loss.backward();warm.step()
            optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=decay)
            loader=DataLoader(TensorDataset(active_arrays['train'],y),batch_size=64,shuffle=True,generator=torch.Generator().manual_seed(seed))
            best=float('inf');best_state=None;stale=0;best_epoch=0
            for epoch in range(1,251):
                model.train()
                for batch,target in loader:
                    optimizer.zero_grad(set_to_none=True);loss=torch.nn.functional.mse_loss(model(batch),target)
                    loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step()
                model.eval()
                with torch.inference_mode():pred=model(active_arrays['validation']).numpy()*target_scale+target_mean
                score=metrics(frames['validation'].YIELD,pred)['RMSE']
                if score<best-1e-6:best=score;best_state=copy.deepcopy(model.state_dict());best_epoch=epoch;stale=0
                else:stale+=1
                if stale>=30:break
            model.load_state_dict(best_state);model.eval()
            cfg=dict(seed=seed,lr=lr,weight_decay=decay,dropout=dropout,best_epoch=best_epoch,validation_RMSE=best,use_year_trend=use_year)
            history.append(cfg);candidates.append((best,model,cfg));print(json.dumps(cfg),flush=True)
            (run/'progress.json').write_text(json.dumps({'status':'validation_search','fits':history},indent=2))
    _,model,cfg=min(candidates,key=lambda x:x[0])
    if not cfg['use_year_trend']:
        for values in arrays.values():values[:,input_count]=0
    measured={}
    for s,f in frames.items():
        with torch.inference_mode():pred=model(arrays[s]).numpy()*target_scale+target_mean
        measured[s]=metrics(f.YIELD,pred)
    # The tree is a separately selected benchmark, not an ensemble component.
    trees=[]
    for leaves in (7,15,31):
        tree=HistGradientBoostingRegressor(max_leaf_nodes=leaves,max_iter=250,learning_rate=.04,l2_regularization=1,random_state=42)
        tree.fit(x['train'],train.YIELD);score=metrics(frames['validation'].YIELD,tree.predict(x['validation']))['RMSE']
        trees.append((score,tree,leaves))
    _,tree,leaves=min(trees,key=lambda z:z[0])
    tree_metrics={s:metrics(f.YIELD,tree.predict(x[s])) for s,f in frames.items()}
    with (run/'tree.pkl').open('wb') as f:pickle.dump(tree,f)
    configuration={**cfg,'input_count':input_count,'target_mean':target_mean,'target_scale':target_scale,'year_mean':year_mean,'year_scale':year_scale,
                   'district_vocabulary':vocab,'season_context':True,'warm_baseline':True}
    torch.save({'state_dict':model.state_dict(),'configuration':configuration},run/'model.pt')
    bundle={'configuration':configuration,'metrics':measured,'tree_metrics':tree_metrics,'tree_leaves':leaves,
            'predictor_columns':names+['FYEAR_scaled','district_index'],'numeric':numeric,'model_kind':'contextual_mlp',
            'search':history,'split_rows':{s:len(f) for s,f in frames.items()},
            'split_years':{'train':[2001,2020],'validation':[2021,2022],'test':[2023,2024]},
            'source_master_sha256':hashlib.sha256((ROOT/'DATASET/candidates/recent_yield/rice_master.csv').read_bytes()).hexdigest(),
            'selection':'Minimum validation RMSE. Test used only after selection. Different cohort/calendar from old reported metrics.',
            'status':'trained_not_activated','scope':'Retrospective seasonal district yield, not a validated current-season farm forecast.'}
    (run/'bundle.json').write_text(json.dumps(bundle,indent=2),encoding='utf-8')
    (directory.parent/'manifest.json').write_text(json.dumps({k:bundle[k] for k in ('predictor_columns','split_rows','split_years','source_master_sha256','scope')},indent=2),encoding='utf-8')
    (run/'progress.json').write_text(json.dumps({'status':'complete','metrics':measured,'tree_metrics':tree_metrics},indent=2))
    print(json.dumps({'metrics':measured,'tree_metrics':tree_metrics}),flush=True)


if __name__=='__main__':main()
