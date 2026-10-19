"""Predeclared validation search adding explicit year trend and district context.

The extra features are legitimate observed inputs, never target encodings.
Training-only district vocabulary; unknown districts map to index zero. Evaluation
is chronological within the historical cohort, not a claim of spatial transfer.
"""
import argparse
import copy
import json
import sys
from pathlib import Path
import numpy as np
import torch
from torch.utils.data import DataLoader,TensorDataset

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from APP.models.contextual_yield import ContextualYield
from APP.training.train import load_data,metrics


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--warm-baseline',action='store_true')
    parser.add_argument('--season-context',action='store_true')
    args=parser.parse_args();args.output.mkdir(parents=True,exist_ok=False)
    torch.set_num_threads(1)
    manifest,arms=load_data();parts=arms['standard'];train=parts['train']['frame']
    keys=train.STATE+'|'+train.DISTRICT
    if args.season_context:keys=keys+'|'+train.SEASON
    vocabulary={key:i+1 for i,key in enumerate(sorted(keys.unique()))}
    year_mean=float(train.FYEAR.mean());year_scale=float(train.FYEAR.std(ddof=0))
    mean=float(parts['train']['y'].mean());scale=float(parts['train']['y'].std())
    arrays={}
    for split,part in parts.items():
        frame=part['frame'];key=frame.STATE+'|'+frame.DISTRICT
        if args.season_context:key=key+'|'+frame.SEASON
        districts=key.map(vocabulary).fillna(0).to_numpy(np.float32)
        arrays[split]=torch.from_numpy(np.column_stack([part['x'],(frame.FYEAR-year_mean)/year_scale,districts]).astype(np.float32))
    y=torch.from_numpy((parts['train']['y']-mean)/scale)
    candidates=[];history=[]
    for lr,decay,dropout in [(.001,.01,.35),(.0003,.01,.35),(.001,.1,.5)]:
        for seed in (42,73,101):
            torch.manual_seed(seed)
            model=ContextualYield(len(vocabulary),dropout)
            if args.warm_baseline:
                # Train a regional-seasonal offset and global trend using ONLY
                # training labels. This is a learned model initialization, not
                # a yield-derived feature passed into validation/test rows.
                with torch.no_grad():
                    model.weather.network[-1].weight.zero_();model.weather.network[-1].bias.zero_()
                warm=torch.optim.AdamW(list(model.district.parameters())+list(model.trend.parameters()),lr=.03,weight_decay=.1)
                for _ in range(500):
                    warm.zero_grad(set_to_none=True)
                    pred=model.district(arrays['train'][:,29].long()).squeeze(-1)+model.trend(arrays['train'][:,28:29]).squeeze(-1)
                    loss=torch.nn.functional.mse_loss(pred,y);loss.backward();warm.step()
            optimizer=torch.optim.AdamW(model.parameters(),lr=lr,weight_decay=decay)
            loader=DataLoader(TensorDataset(arrays['train'],y),batch_size=64,shuffle=True,generator=torch.Generator().manual_seed(seed))
            best=float('inf');state=None;stale=0;best_epoch=0
            for epoch in range(1,251):
                model.train()
                for x,target in loader:
                    optimizer.zero_grad(set_to_none=True)
                    loss=torch.nn.functional.mse_loss(model(x),target)
                    loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step()
                model.eval()
                with torch.inference_mode():pred=model(arrays['validation']).numpy()*scale+mean
                score=metrics(parts['validation']['y'],pred)['RMSE']
                if score<best-1e-6:best=score;state=copy.deepcopy(model.state_dict());stale=0;best_epoch=epoch
                else:stale+=1
                if stale>=30:break
            model.load_state_dict(state);model.eval()
            item={'seed':seed,'lr':lr,'weight_decay':decay,'dropout':dropout,'best_epoch':best_epoch,'validation_RMSE':best}
            history.append(item);candidates.append((best,model,item))
            print(json.dumps(item),flush=True)
            (args.output/'progress.json').write_text(json.dumps({'status':'validation_search','fits':history},indent=2))
    _,model,selected=min(candidates,key=lambda item:item[0])
    measured={}
    for split in parts:
        with torch.inference_mode():pred=model(arrays[split]).numpy()*scale+mean
        measured[split]=metrics(parts[split]['y'],pred)
    configuration={**selected,'target_mean':mean,'target_scale':scale,'year_mean':year_mean,'year_scale':year_scale,
                   'district_vocabulary':vocabulary,'season_context':args.season_context,'warm_baseline':args.warm_baseline}
    torch.save({'state_dict':model.state_dict(),'configuration':configuration},args.output/'model.pt')
    bundle={'model_kind':'contextual_mlp','configuration':configuration,'metrics':measured,'search':history,
        'predictor_columns':manifest['standard']['predictor_columns']+['FYEAR_scaled','district_index'],
        'selection':'Minimum validation RMSE; test evaluated only after selection.',
        'training_data_sha256':parts['train']['sha256'],'status':'trained_not_activated',
        'scope':'Historical known-district temporal estimation; not spatial generalization.'}
    (args.output/'bundle.json').write_text(json.dumps(bundle,indent=2)+'\n')
    (args.output/'progress.json').write_text(json.dumps({'status':'complete','metrics':measured},indent=2))
    print(json.dumps({'selected':selected,'metrics':measured}),flush=True)


if __name__=='__main__':main()
