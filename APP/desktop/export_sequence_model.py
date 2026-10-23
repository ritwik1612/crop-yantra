"""Export the frozen validation-selected CNN-LSTM and train-only scenario templates."""
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
import onnxruntime as ort

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from APP.models.temporal import YieldCNNLSTM


class RuntimeCNNLSTM(nn.Module):
    """Unidirectional LSTM: gathering last valid output equals packed hidden state."""
    def __init__(self,model,mean,scale):
        super().__init__();self.model=model;self.mean=mean;self.scale=scale
    def forward(self,weather,lengths,static):
        mask=(torch.arange(weather.shape[1],device=weather.device)[None,:]<lengths[:,None])[:,None,:]
        first=torch.nn.functional.gelu(self.model.conv1(weather.transpose(1,2)*mask))*mask
        x=torch.nn.functional.gelu(self.model.conv2(first))*mask
        output,_=self.model.lstm(x.transpose(1,2))
        index=(lengths-1)[:,None,None].expand(-1,1,output.shape[-1])
        hidden=output.gather(1,index).squeeze(1)
        joined=torch.cat([hidden,static],1)
        dense=self.model.head[2](self.model.head[1](self.model.head[0](joined)))
        z=self.model.head[3](dense).squeeze(-1)
        return z*self.scale+self.mean,z,x.transpose(1,2),output,joined,dense,first.transpose(1,2)


def main():
    torch.set_num_threads(4)
    run=ROOT/'APP/training/runs/sequences_20261023_cpu'
    data=ROOT/'DATASET/training/sequences_lead60'
    runtime=ROOT/'APP/prototype/runtime'
    result=json.loads((run/'result.json').read_text())
    manifest=json.loads((run/'data_manifest.json').read_text())
    if result['selected']['model']!='cnn_lstm':raise ValueError('Expected frozen CNN-LSTM winner')
    saved=torch.load(run/result['selected']['checkpoint'],weights_only=True)
    model=YieldCNNLSTM(saved['static_dim'],saved['weather_dim'],saved['hidden_dim']).eval()
    model.load_state_dict(saved['state_dict'])
    wrapped=RuntimeCNNLSTM(model,manifest['target_mean'],manifest['target_scale']).eval()
    sample=dict(np.load(data/'validation.npz'))
    inputs=tuple(torch.from_numpy(sample[k][:4]) for k in ['weather','lengths','static'])
    path=runtime/'yield-sequence.onnx'
    torch.onnx.export(wrapped,inputs,str(path),opset_version=17,dynamo=False,
                      input_names=['weather','lengths','static'],
                      output_names=['yield_t_ha','normalized_yield','conv_features','lstm_states','joined','dense','conv1_features'],
                      dynamic_axes={k:{0:'batch'} for k in ['weather','lengths','static','yield_t_ha','normalized_yield','conv_features','lstm_states','joined','dense','conv1_features']})
    session=ort.InferenceSession(str(path),providers=['CPUExecutionProvider'])
    errors={}
    # Parity is a deployment check, not additional test-driven model selection.
    for split in ['train','validation','test']:
        a=dict(np.load(data/f'{split}.npz'))
        with torch.inference_mode():
            expected=model(*(torch.from_numpy(a[k]) for k in ['weather','lengths','static'])).numpy()*manifest['target_scale']+manifest['target_mean']
        actual=session.run(None,{k:a[k] for k in ['weather','lengths','static']})[0]
        errors[split]=float(np.max(np.abs(actual-expected)))
        if errors[split]>2e-5:raise ValueError(f'ONNX parity failed: {errors}')
    tr=dict(np.load(data/'train.npz'));records=pd.read_csv(data/'train_records.csv')
    master=pd.read_csv(ROOT/'DATASET/merged/rice_master.csv')
    train=master[master.FYEAR<=2020]
    wm=np.array(manifest['weather_mean']);ws=np.array(manifest['weather_scale'])
    raw=tr['weather']*ws+wm
    groups={}
    for (gid,season),idx in records.groupby(['IDREGION','SEASON']).groups.items():
        indexes=list(idx); lengths=tr['lengths'][indexes];length=int(np.median(lengths))
        sequence=[]
        for t in range(length):
            available=[i for i in indexes if tr['lengths'][i]>t]
            sequence.append(np.median(raw[available,t,:],axis=0).tolist())
        info=train[(train.IDREGION==gid)&(train.SEASON==season)].iloc[0]
        groups[f'{gid}|{season}']={'weather':sequence,'state':info.STATE,'district':info.DISTRICT,
            'coordinates':[float(info.CENTROID_X),float(info.CENTROID_Y)],
            'years':sorted(int(v) for v in records.loc[indexes,'FYEAR']),
            'season_days':float(train[(train.IDREGION==gid)&(train.SEASON==season)].WEATHER_DAY_COUNT.median()),
            'kind':'measured_training_reference','donors':[]}
    # Existing map coverage determines supported targets; never reuse its trees or labels.
    old=json.loads((runtime/'spatial-coverage.json').read_text())
    prep=json.loads((runtime/'preprocessor.json').read_text())
    lon,lat=[prep['numeric'].index(k) for k in ['CENTROID_X','CENTROID_Y']]
    for key,refs in old['references'].items():
        if key in groups:continue
        gid,season=key.split('|');ref=refs[0]
        coordinates=np.array([ref['numeric'][lon],ref['numeric'][lat]])
        pool=[(k,v) for k,v in groups.copy().items() if k.endswith('|'+season) and v['kind']=='measured_training_reference']
        local=[item for item in pool if item[1]['state']==ref['state']]
        if local:pool=local
        def distance(item):
            xy=np.array(item[1]['coordinates']);delta=xy-coordinates
            return float(np.hypot(delta[0]*np.cos(np.deg2rad(coordinates[1])),delta[1])*111.195)
        donors=sorted(pool,key=distance)[:3]
        if not donors:continue
        weights=1/np.maximum([distance(d) for d in donors],1);weights=weights/weights.sum()
        length=min(len(d[1]['weather']) for d in donors)
        weather=sum(w*np.array(d[1]['weather'][:length]) for w,d in zip(weights,donors))
        groups[key]={'weather':weather.tolist(),'coordinates':coordinates.tolist(),
            'state':ref['state'],'district':ref['district'],
            'years':sorted(set(y for _,d in donors for y in d['years'])),
            'season_days':float(sum(w*d['season_days'] for w,(_,d) in zip(weights,donors))),
            'kind':'synthetic_neighbour_transfer',
            'donors':[{'district':d['district'],'state':d['state'],'distanceKm':distance(item),'weight':float(w)} for w,item in zip(weights,donors) for d in [item[1]]]}
    category_reference={c:str(records[c].mode().iloc[0]) for c in ['STATE','SEASON']}
    config={**manifest,'model':'CNN–LSTM yield regressor','model_kind':'cnn_lstm',
            'architecture':['Conv1d(11,32,k=3)','GELU','Conv1d(32,32,k=3)','GELU','LSTM(32,32)',
                            'Concatenate 11 static inputs','Linear(43,64)','GELU','Linear(64,1)'],
            'best_epoch':saved['best_epoch'],'test':result['test'],'validation':result['selected']['validation'],
            'export_max_error':errors,'export_verified_rows':2642,'category_reference':category_reference,
            'selection':'Architecture, seed and checkpoint frozen by validation RMSE; test evaluated once.'}
    (runtime/'sequence-config.json').write_text(json.dumps(config,indent=2),encoding='utf-8')
    (runtime/'sequence-references.json').write_text(json.dumps(groups,separators=(',',':')),encoding='utf-8')
    meta=json.loads((runtime/'metadata.json').read_text())
    if meta.get('yield_default_model')!='cnn_lstm':
        meta['archived_tree_benchmark']={'model':meta['yield_model'],'test':meta['yield_test']}
    meta.update(version='2.0',yield_default_model='cnn_lstm',yield_model=config['model'],
                yield_test=config['test'],yield_sequence=config,yield_neural_only=True)
    (runtime/'metadata.json').write_text(json.dumps(meta,separators=(',',':')),encoding='utf-8')
    print(json.dumps({'parity':errors,'references':len(groups),'model':config['model']}),flush=True)


if __name__=='__main__':main()
