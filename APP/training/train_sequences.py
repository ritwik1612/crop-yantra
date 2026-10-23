"""Prepare real weather sequences and train CPU neural yield candidates.

No active app artifacts are overwritten. Validation selects epochs/configuration;
held-out test evaluation is explicit and is not used for selection.
"""
import argparse
import copy
import hashlib
import json
import math
import re
import sys
from datetime import date, timedelta, datetime
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from APP.models.temporal import YieldLSTM, MaskedYieldCNN, YieldCNNLSTM

CHANNELS = ['TMAX','TMIN','TAVG','VPRES','WSPD','PREC','ET0','RAD','RELH','PS']
PARAMS = dict(TMAX='T2M_MAX', TMIN='T2M_MIN', TAVG='T2M', WSPD='WS2M',
              PREC='PRECTOTCORR', ET0='EVLAND', RAD='ALLSKY_SFC_SW_DWN', RELH='RH2M', PS='PS')
STATES = ['Andhra Pradesh','Karnataka','Tamil Nadu','Telangana']
SEASONS = ['Kharif','Rabi','Summer','Autumn','Winter']
MODELS = {'lstm': YieldLSTM, 'cnn': MaskedYieldCNN, 'cnn_lstm': YieldCNNLSTM}


def key(value):
    return re.sub('[^A-Z0-9]', '', str(value).upper().replace('&','AND'))


def window(year, season):
    ranges = {'Kharif': (year,6,1,year,12,1), 'Rabi': (year,11,1,year+1,5,1),
              'Summer': (year+1,3,1,year+1,7,1), 'Autumn': (year,9,1,year+1,1,1),
              'Winter': (year,12,1,year+1,4,1)}
    values = ranges[season]
    return date(*values[:3]), date(*values[3:])


def metrics(actual, predicted):
    residual = np.asarray(actual) - np.asarray(predicted)
    denominator = np.square(actual - np.mean(actual)).sum()
    return {'MAE': float(np.abs(residual).mean()), 'RMSE': float(np.sqrt(np.square(residual).mean())),
            'R2': float(1 - np.square(residual).sum()/denominator) if denominator else None}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(destination, lead_days):
    master_path = ROOT/'DATASET/merged/rice_master.csv'
    daily_path = ROOT/'DATASET/raw/weather/daily_weather.csv'
    frame = pd.read_csv(master_path)
    if frame.duplicated(['IDREGION','FYEAR','SEASON']).any():
        raise ValueError('Duplicate observation keys')
    if not set(frame.SEASON).issubset(SEASONS):
        raise ValueError('Unknown seasonal calendar')
    daily = pd.read_csv(daily_path)
    weather = {}
    # Only exact state + district IDs are accepted. No neighbouring yield labels.
    for (state, district, gid), _ in frame.groupby(['STATE','DISTRICT','IDREGION']):
        source = 'IND_' + key(state) + '_' + key(district)
        part = daily[daily.IDREGION == source]
        weather[gid] = {r.DATE: [getattr(r,c) for c in CHANNELS] for r in part.itertuples(index=False)}
    cache_files = sorted((ROOT/'DATASET/raw/weather/nasa_recent').glob('*.json'))
    for path in cache_files:
        gid = path.name.rsplit('_',2)[0]
        if gid not in weather:
            continue
        blob = json.loads(path.read_text(encoding='utf-8'))
        params = blob['properties']['parameter']
        for day in params['T2M']:
            values = {name: params[param][day] for name,param in PARAMS.items()}
            if not all(isinstance(v,(float,int)) and math.isfinite(v) and v != -999 for v in values.values()):
                continue
            values['VPRES'] = 6.108 * math.exp(17.27*values['TAVG']/(values['TAVG']+237.3))*values['RELH']/100
            text = f'{day[:4]}-{day[4:6]}-{day[6:]}'
            weather[gid][text] = [values[c] for c in CHANNELS]
    sequences, static, rows, excluded, audit = [], [], [], [], []
    for record in frame.to_dict('records'):
        start, end = window(int(record['FYEAR']), record['SEASON'])
        days = [start + timedelta(days=i) for i in range((end-start).days)]
        lookup = weather[record['IDREGION']]
        if any(d.isoformat() not in lookup for d in days):
            excluded.append({k:record[k] for k in ['IDREGION','FYEAR','SEASON']})
            continue
        full = np.array([lookup[d.isoformat()] for d in days], dtype=np.float64)
        if not np.isfinite(full).all() or np.any(full == -999):
            raise ValueError('Invalid daily weather')
        # Reconcile every joined weather season with the existing merged record.
        for channel in CHANNELS:
            index = CHANNELS.index(channel)
            total = channel in ['PREC','ET0','RAD']
            observed = full[:,index].sum() if total else full[:,index].mean()
            column = channel + ('_TOTAL' if total else '_MEAN')
            tolerance = .03 if total else .005
            if abs(observed - record[column]) > tolerance:
                raise ValueError(f'Weather join audit failed: {record["IDREGION"]} {record["FYEAR"]} {column}: {observed} != {record[column]}')
        available = full[:len(days)-lead_days] if lead_days else full
        if not len(available):
            raise ValueError('Lead time removes all weather')
        # Ten-day bins preserve time order; totals for rainfall/evaporation/radiation.
        bins = []
        for offset in range(0,len(available),10):
            block = available[offset:offset+10]
            b = block.mean(axis=0)
            for c in ['PREC','ET0','RAD']:
                b[CHANNELS.index(c)] = block[:,CHANNELS.index(c)].sum()
            bins.append(np.r_[b,len(block)])
        sequences.append(np.array(bins,dtype=np.float32))
        # Deliberately exclude production, yield-derived features and end-season area.
        static.append([record['CENTROID_X'],record['CENTROID_Y']] +
                      [float(record['STATE']==s) for s in STATES] +
                      [float(record['SEASON']==s) for s in SEASONS])
        rows.append({**{k:record[k] for k in ['IDREGION','STATE','DISTRICT','FYEAR','SEASON','YIELD']},
                     'weather_start': start.isoformat(),
                     'last_weather_date': days[len(available)-1].isoformat(),
                     'season_end_exclusive': end.isoformat(), 'steps':len(bins)})
    records = pd.DataFrame(rows)
    if len(records) != len(frame):
        raise ValueError(f'Missing daily weather for {len(excluded)} rows; refusing silent split changes: {excluded[:8]}')
    years = records.FYEAR.to_numpy()
    splits = {'train': years<=2020, 'validation':(years>=2021)&(years<=2022), 'test':years>=2023}
    if any(not m.any() for m in splits.values()):
        raise ValueError('Empty chronological split')
    nsteps = max(len(s) for s in sequences)
    valid_train = np.concatenate([s for s,m in zip(sequences,splits['train']) if m])
    mean = valid_train.mean(axis=0); scale = valid_train.std(axis=0); scale[scale<1e-6]=1
    static = np.array(static,dtype=np.float32)
    static_mean = static[splits['train'],:2].mean(axis=0)
    static_scale = static[splits['train'],:2].std(axis=0); static_scale[static_scale<1e-6]=1
    static[:,:2] = (static[:,:2]-static_mean)/static_scale
    y = records.YIELD.to_numpy(dtype=np.float32)
    target_mean = float(y[splits['train']].mean()); target_scale = float(y[splits['train']].std())
    padded = np.zeros((len(rows),nsteps,len(mean)),dtype=np.float32)
    lengths = np.array([len(s) for s in sequences],dtype=np.int64)
    for i,s in enumerate(sequences): padded[i,:len(s)] = (s-mean)/scale
    destination.mkdir(parents=True,exist_ok=True)
    for split,mask in splits.items():
        np.savez_compressed(destination/f'{split}.npz',weather=padded[mask],lengths=lengths[mask],
                            static=static[mask],target=(y[mask]-target_mean)/target_scale,yield_t_ha=y[mask])
        records.loc[mask].to_csv(destination/f'{split}_records.csv',index=False)
    manifest = {'rows':len(rows),'splits':{s:int(m.sum()) for s,m in splits.items()},
                'weather_channels': CHANNELS+['BIN_DAY_COUNT'],
                'static_features':['CENTROID_X','CENTROID_Y']+['STATE_'+s for s in STATES]+['SEASON_'+s for s in SEASONS],
                'lead_days':lead_days,'bin_days':10,'max_steps':nsteps,
                'weather_mean':mean.tolist(),'weather_scale':scale.tolist(),
                'coordinate_mean':static_mean.tolist(),'coordinate_scale':static_scale.tolist(),
                'target_mean':target_mean,'target_scale':target_scale,
                'master_sha256':digest(master_path),'daily_weather_sha256':digest(daily_path),
                'nasa_cache_sha256':{p.name:digest(p) for p in cache_files},
                'weather_join_audited':True,'excluded_rows':len(excluded),
                'limitations':['Season windows are calendar proxies, not observed harvest dates.',
                              'EVLAND is land evaporation, not reference evapotranspiration.',
                              '60-day lead is relative to proxy season end; not real-time operational validation.',
                              'Existing full-season MLP metrics are not a like-for-like forecast comparison.',
                              'Coordinates are boundary representative points, not farm observations.'],
                'target':'Observed production tonnes / crop area hectares; no synthetic targets',
                'fit_policy':'Scalers fit on training observations only; padding excluded'}
    (destination/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'prepared':str(destination),'splits':manifest['splits'],'weather_join_audited':True}),flush=True)
    return manifest


def predict(model, arrays):
    model.eval()
    with torch.inference_mode():
        return model(torch.from_numpy(arrays['weather']),torch.from_numpy(arrays['lengths']),
                     torch.from_numpy(arrays['static'])).numpy()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-dir',type=Path,required=True)
    parser.add_argument('--data-dir',type=Path,default=ROOT/'DATASET/training/sequences_lead60')
    parser.add_argument('--epochs',type=int,default=150)
    parser.add_argument('--patience',type=int,default=25)
    parser.add_argument('--lead-days',type=int,default=60)
    parser.add_argument('--train',action='store_true')
    parser.add_argument('--evaluate-test',action='store_true')
    args = parser.parse_args()
    if not 0<=args.lead_days<=60: raise ValueError('Lead days must be between 0 and 60')
    if args.run_dir.exists(): raise FileExistsError('Use a new run directory; existing results are immutable')
    torch.set_num_threads(4)
    manifest = prepare(args.data_dir,args.lead_days)
    if not args.train: return
    args.run_dir.mkdir(parents=True)
    (args.run_dir/'data_manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    arrays = {s:dict(np.load(args.data_dir/f'{s}.npz')) for s in ['train','validation']}
    tr,va=arrays['train'],arrays['validation']
    candidates=[]
    for name,cls in MODELS.items():
        for seed in [42,73]:
            torch.manual_seed(seed); np.random.seed(seed)
            model=cls(tr['static'].shape[1],tr['weather'].shape[2],hidden_dim=32)
            optimizer=torch.optim.AdamW(model.parameters(),lr=.001,weight_decay=.01)
            dataset=TensorDataset(*(torch.from_numpy(tr[k]) for k in ['weather','lengths','static','target']))
            loader=DataLoader(dataset,batch_size=64,shuffle=True,generator=torch.Generator().manual_seed(seed))
            best=float('inf'); state=None; stale=0; history=[]; best_epoch=0
            print(json.dumps({'starting':name,'seed':seed,'device':'cpu'}),flush=True)
            for epoch in range(1,args.epochs+1):
                model.train(); losses=[]
                for weather,lengths,static,target in loader:
                    optimizer.zero_grad(set_to_none=True)
                    loss=torch.nn.functional.mse_loss(model(weather,lengths,static),target)
                    loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),5);optimizer.step()
                    losses.append(float(loss.detach()))
                valpred=predict(model,va)*manifest['target_scale']+manifest['target_mean']
                score=metrics(va['yield_t_ha'],valpred)
                history.append({'epoch':epoch,'train_mse_scaled':float(np.mean(losses)),**score})
                if score['RMSE']<best-1e-6:
                    best=score['RMSE'];state=copy.deepcopy(model.state_dict());stale=0;best_epoch=epoch
                else: stale+=1
                if epoch==1 or epoch%10==0:
                    print(json.dumps({'model':name,'seed':seed,'epoch':epoch,'validation':score}),flush=True)
                if stale>=args.patience: break
            model.load_state_dict(state)
            tag=f'{name}_seed{seed}'
            torch.save({'state_dict':state,'model':name,'seed':seed,'hidden_dim':32,
                        'weather_dim':tr['weather'].shape[2],'static_dim':tr['static'].shape[1],
                        'best_epoch':best_epoch},args.run_dir/f'{tag}.pt')
            (args.run_dir/f'{tag}_history.json').write_text(json.dumps(history,indent=2),encoding='utf-8')
            prediction=predict(model,va)*manifest['target_scale']+manifest['target_mean']
            np.save(args.run_dir/f'{tag}_validation_predictions.npy',prediction)
            candidates.append({'model':name,'seed':seed,'checkpoint':f'{tag}.pt','best_epoch':best_epoch,
                               'validation':metrics(va['yield_t_ha'],prediction)})
            (args.run_dir/'candidates.json').write_text(json.dumps(candidates,indent=2),encoding='utf-8')
    selected=min(candidates,key=lambda c:c['validation']['RMSE'])
    result={'status':'validation_selected','device':'cpu','selected':selected,'candidates':candidates,
            'test_used_for_selection':False,'app_activated':False,
            'training_mean_baseline_validation':metrics(va['yield_t_ha'],np.full_like(va['yield_t_ha'],manifest['target_mean']))}
    # Only the frozen validation winner is evaluated on test, once.
    if args.evaluate_test:
        checkpoint=torch.load(args.run_dir/selected['checkpoint'],weights_only=True)
        model=MODELS[selected['model']](checkpoint['static_dim'],checkpoint['weather_dim'],checkpoint['hidden_dim'])
        model.load_state_dict(checkpoint['state_dict'])
        test=dict(np.load(args.data_dir/'test.npz'))
        predictions=predict(model,test)*manifest['target_scale']+manifest['target_mean']
        result['test']=metrics(test['yield_t_ha'],predictions)
        records=pd.read_csv(args.data_dir/'test_records.csv');records['predicted_yield_t_ha']=predictions
        records.to_csv(args.run_dir/'selected_test_predictions.csv',index=False)
        result['status']='evaluated_not_deployed'
    (args.run_dir/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


if __name__=='__main__': main()
