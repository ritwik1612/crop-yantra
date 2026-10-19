"""Validation-only MLP tuning; evaluate the locked test split after selection.

Keeps the original data/transforms and checkpoints. No fabricated observations,
target leakage, test-driven search, or model activation. Results are machine
training artifacts, not a user-facing report.
"""
import argparse
import copy
import json
import random
import sys
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from APP.models.tabular import YieldMLP
from APP.training.train import load_data, metrics


def fit(parts, config, seed, epochs):
    random.seed(seed);np.random.seed(seed);torch.manual_seed(seed)
    model=YieldMLP(28)
    model.network[2].p=config['dropout']
    mean=float(parts['train']['y'].mean());scale=float(parts['train']['y'].std())
    x=torch.from_numpy(parts['train']['x'])
    y=torch.from_numpy((parts['train']['y']-mean)/scale)
    vx=torch.from_numpy(parts['validation']['x'])
    loader=DataLoader(TensorDataset(x,y),batch_size=64,shuffle=True,
                      generator=torch.Generator().manual_seed(seed))
    optimizer=torch.optim.AdamW(model.parameters(),lr=config['lr'],weight_decay=config['weight_decay'])
    best=float('inf');state=None;best_epoch=0;stale=0
    for epoch in range(1,epochs+1):
        model.train()
        for inputs,targets in loader:
            optimizer.zero_grad(set_to_none=True)
            loss=torch.nn.functional.mse_loss(model(inputs),targets)
            loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step()
        model.eval()
        with torch.inference_mode():pred=model(vx).numpy()*scale+mean
        rmse=metrics(parts['validation']['y'],pred)['RMSE']
        if rmse<best-1e-6:
            best=rmse;state=copy.deepcopy(model.state_dict());best_epoch=epoch;stale=0
        else:stale+=1
        if stale>=25:break
    model.load_state_dict(state);model.eval()
    with torch.inference_mode():pred=model(vx).numpy()*scale+mean
    return model,pred,{'seed':seed,'best_epoch':best_epoch,'configuration':config,'validation_RMSE':best}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--epochs',type=int,default=200)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    manifest,arms=load_data();parts=arms['standard']
    candidates=[];records=[]
    # A predeclared small search, chosen before looking at new test predictions.
    configs=[{'lr':lr,'weight_decay':decay,'dropout':dropout}
             for lr,decay,dropout in [(.001,.01,.35),(.0003,.01,.2),(.001,.1,.35),(.0005,.1,.5),(.0003,.001,.35)]]
    for config in configs:
        models=[];predictions=[];details=[]
        for seed in (42,73,101):
            model,pred,record=fit(parts,config,seed,args.epochs)
            models.append(model);predictions.append(pred);details.append(record);records.append(record)
            print(json.dumps(record),flush=True)
            # Single-model candidates and an average ensemble are both selected
            # solely using validation RMSE; no test scores enter this loop.
            candidates.append((record['validation_RMSE'],[model],[record]))
            (args.output/'progress.json').write_text(json.dumps({'status':'validation_search','fits':records},indent=2))
        score=metrics(parts['validation']['y'],np.mean(predictions,axis=0))['RMSE']
        candidates.append((score,models,details))
    score,models,details=min(candidates,key=lambda item:item[0])
    mean=float(parts['train']['y'].mean());scale=float(parts['train']['y'].std())
    evaluation={}
    for split in ('train','validation','test'):
        with torch.inference_mode():
            values=torch.from_numpy(parts[split]['x'])
            pred=np.mean([model(values).numpy()*scale+mean for model in models],axis=0)
        evaluation[split]=metrics(parts[split]['y'],pred)
    states=[model.state_dict() for model in models]
    torch.save({'state_dicts':states,'configuration':{'target_mean':mean,'target_scale':scale},'members':details},args.output/'model.pt')
    bundle={'model_kind':'mlp_ensemble' if len(models)>1 else 'mlp','representation':'standard',
        'predictor_columns':manifest['standard']['predictor_columns'],
        'configuration':{'target_mean':mean,'target_scale':scale,'members':details},
        'metrics':evaluation,'selection':'Lowest chronological validation RMSE; test evaluated only after configuration/ensemble selection.',
        'training_data_sha256':parts['train']['sha256'],'search':records,
        'status':'trained_not_activated','architecture':[28,64,32,1],'ensemble_size':len(models)}
    (args.output/'bundle.json').write_text(json.dumps(bundle,indent=2)+'\n')
    (args.output/'progress.json').write_text(json.dumps({'status':'complete','metrics':evaluation,'members':len(models)},indent=2))
    print(json.dumps({'selected_validation_RMSE':score,'members':len(models),'metrics':evaluation}),flush=True)


if __name__=='__main__':main()
