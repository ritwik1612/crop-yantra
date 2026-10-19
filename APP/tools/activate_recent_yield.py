"""Export validation-selected recent models; verify parity before activation.

The tree is selected as default by validation RMSE, not held-out test score.
Preserve the complete former runtime and master for rollback.
"""
import hashlib
import json
import pickle
import shutil
import sys
from pathlib import Path
import numpy as np
import onnxruntime as ort
import pandas as pd
import torch

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from APP.models.contextual_yield import ContextualYield
from APP.desktop.export_yield_mlp import PhysicalYield


def main():
    torch.set_num_threads(1)
    run=ROOT/'APP/training/runs/recent_yield_20261019';runtime=ROOT/'APP/prototype/runtime'
    bundle=json.loads((run/'bundle.json').read_text());cfg=bundle['configuration']
    stage=run/'runtime';stage.mkdir(exist_ok=True)
    checkpoint=torch.load(run/'model.pt',map_location='cpu',weights_only=True)
    net=ContextualYield(len(cfg['district_vocabulary']),cfg['dropout'],cfg['input_count'])
    net.load_state_dict(checkpoint['state_dict']);graph=PhysicalYield(net,cfg['target_mean'],cfg['target_scale']).eval()
    torch.onnx.export(graph,(torch.zeros(1,cfg['input_count']+2),),str(stage/'yield-mlp.onnx'),input_names=['features'],
                      output_names=['yield_t_per_ha'],dynamic_axes={'features':{0:'batch'},'yield_t_per_ha':{0:'batch'}},opset_version=17,dynamo=False)
    with (run/'preprocessor.pkl').open('rb') as f:prep=pickle.load(f)
    with (run/'tree.pkl').open('rb') as f:tree=pickle.load(f)
    numeric=bundle['numeric'];pipe=prep.named_transformers_['numeric'];imputer,scaler=pipe.named_steps.values()
    config={'numeric':numeric,'median':imputer.statistics_.tolist(),'mean':scaler.mean_.tolist(),'scale':scaler.scale_.tolist(),
            'categories':[c.tolist() for c in prep.named_transformers_['categorical'].categories_], 'predictors':prep.get_feature_names_out().tolist()}
    master=pd.read_csv(ROOT/'DATASET/candidates/recent_yield/rice_master.csv');x=prep.transform(master[numeric+['STATE','SEASON']]).astype(np.float32)
    keys=master.STATE+'|'+master.DISTRICT+'|'+master.SEASON
    inputs=np.column_stack([x,(master.FYEAR-cfg['year_mean'])/cfg['year_scale'],keys.map(cfg['district_vocabulary']).fillna(0)]).astype(np.float32)
    if not cfg.get('use_year_trend',True):inputs[:,cfg['input_count']]=0
    with torch.inference_mode():expected=graph(torch.from_numpy(inputs)).numpy()
    session=ort.InferenceSession(str(stage/'yield-mlp.onnx'),providers=['CPUExecutionProvider'])
    actual=session.run(None,{'features':inputs})[0]
    np.testing.assert_allclose(actual,expected,atol=2e-5,rtol=1e-5)
    trees=[]
    for iteration in tree._predictors:
        for t in iteration:
            if t.nodes['is_categorical'].any():raise ValueError('Unsupported categorical tree nodes')
            nodes=[[float(n['value']),int(n['feature_idx']),float(n['num_threshold']),int(n['left']),int(n['right']),bool(n['is_leaf']),bool(n['missing_go_to_left'])] for n in t.nodes]
            for i in reversed(range(len(nodes))):
                if not nodes[i][5]:
                    a,b=nodes[i][3:5];ca,cb=int(t.nodes[a]['count']),int(t.nodes[b]['count'])
                    nodes[i][0]=(nodes[a][0]*ca+nodes[b][0]*cb)/(ca+cb)
            trees.append(nodes)
    portable={'baseline':float(tree._baseline_prediction[0,0]),'trees':trees}
    def predict(row):
        result=portable['baseline']
        for t in trees:
            i=0
            while not t[i][5]:i=t[i][3] if row[t[i][1]]<=t[i][2] else t[i][4]
            result+=t[i][0]
        return result
    np.testing.assert_allclose([predict(row) for row in x],tree.predict(x),atol=1e-8)
    history={f'{r.IDREGION}|{int(r.FYEAR)}|{r.SEASON}':{'numeric':[float(r[n]) for n in numeric],'state':r.STATE,'district':r.DISTRICT,
                'observed':float(r.YIELD),'split':'train' if r.FYEAR<=2020 else 'validation' if r.FYEAR<=2022 else 'test'} for _,r in master.iterrows()}
    meta=json.loads((runtime/'metadata.json').read_text());meta['version']='2026-10-19-recent'
    default='gbdt' if bundle['tree_metrics']['validation']['RMSE']<bundle['metrics']['validation']['RMSE'] else 'mlp'
    if default!='gbdt':raise ValueError('Unexpected validation selection; review activation policy')
    meta.update(yield_model='HistGradientBoostingRegressor',yield_test=bundle['tree_metrics']['test'],yield_default_model=default,
                yield_dataset={k:bundle[k] for k in ('split_rows','split_years','source_master_sha256')})
    meta['yield_dataset'].update(rows=len(master),districts=int(master.IDREGION.nunique()),last_agricultural_year='2024–25')
    meta['yield_mlp']={**cfg,'model':'Contextual Residual MLP regressor','model_kind':'contextual_mlp','input_count':cfg['input_count']+2,
                     'architecture':[cfg['input_count'],64,32,1],'activation':'GELU','test':bundle['metrics']['test'],
                     'validation':bundle['metrics']['validation'],'category_reference':{n:str(master[master.FYEAR<=2020][n].mode().iloc[0]) for n in ('STATE','SEASON')},
                     'export_max_error':float(np.max(np.abs(actual-expected))),'checkpoint_sha256':hashlib.sha256((run/'model.pt').read_bytes()).hexdigest(),
                     'selection':'Validation-selected recent neural candidate; weaker than tree on validation and test; experimental, not default',
                     'dataset':meta['yield_dataset']}
    for name,obj in [('preprocessor.json',config),('yield.json',portable),('historical.json',history),('metadata.json',meta)]:
        (stage/name).write_text(json.dumps(obj,allow_nan=False,separators=(',',':')),encoding='utf-8')
    backup=ROOT/'OTHER/model_archive/yield_before_recent_20261019'
    if not backup.exists():
        backup.mkdir(parents=True)
        for name in ('preprocessor.json','yield.json','historical.json','metadata.json','yield-mlp.onnx'):
            shutil.copy2(runtime/name,backup/name)
        shutil.copy2(ROOT/'DATASET/merged/rice_master.csv',backup/'rice_master.csv')
    for path in stage.iterdir():shutil.copy2(path,runtime/path.name)
    shutil.copy2(ROOT/'DATASET/candidates/recent_yield/rice_master.csv',ROOT/'DATASET/merged/rice_master.csv')
    bundle['status']='activated_tree_default_neural_experimental';(run/'bundle.json').write_text(json.dumps(bundle,indent=2),encoding='utf-8')
    print(json.dumps({'default':default,'parity_rows':len(master),'neural_export_max_error':float(np.max(np.abs(actual-expected))),
                      'metrics':bundle['tree_metrics']['test']},indent=2))


if __name__=='__main__':main()
