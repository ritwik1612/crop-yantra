"""Future local inference from complete features and an explicitly chosen bundle.

Never returns a demo fallback. Run only after supervised training; trusted
pickle/PyTorch files are required. This is not connected to the browser beta.
"""
import argparse
import hashlib
import json
import pickle
import sys
from pathlib import Path
import numpy as np
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from APP.models.tabular import YieldMLP
from APP.inference.preprocess import transform_rows

def predict_row(row,bundle_dir):
    folder=Path(bundle_dir)
    if not (folder/'bundle.json').exists(): raise FileNotFoundError('No trained model bundle. Train later; no prediction is available now.')
    info=json.loads((folder/'bundle.json').read_text())
    for name,expected in info['preprocessing_artifact_sha256'].items():
        if hashlib.sha256((ROOT/'pre-processing/artifacts'/name).read_bytes()).hexdigest()!=expected:
            raise ValueError('Preprocessing artifact changed after training; incompatible model bundle')
    features,warnings=transform_rows([row],info['representation'])
    if list(features.columns)!=info['predictor_columns']: raise ValueError('Preprocessing/model schema mismatch')
    x=features.to_numpy(dtype=np.float32)
    if info['model_kind']=='mlp':
        checkpoint=torch.load(folder/'model.pt',map_location='cpu',weights_only=True)
        model=YieldMLP(x.shape[1]);model.load_state_dict(checkpoint['state_dict']);model.eval()
        with torch.no_grad(): value=float(model(torch.tensor(x)).item())
        value=value*info['configuration']['target_scale']+info['configuration']['target_mean']
    elif info['model_kind']=='gbdt':
        with (folder/'model.pkl').open('rb') as handle: model=pickle.load(handle)
        value=float(model.predict(x)[0])
    else: raise ValueError('Unsupported model kind')
    if not np.isfinite(value): raise ValueError('Invalid model output')
    if value<0: warnings.append('Negative regressor output; do not present as an agronomically valid estimate')
    return {'mode':'trained_model','yield_t_per_ha':value,'representation':info['representation'],
            'model':info['model_kind'],'predictor_count':x.shape[1], 'warnings':warnings,
            'explanation':'Complete supplied features transformed with saved preprocessing and passed through trained weights. Feature attribution is not computed.'}

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--features',type=Path,required=True);parser.add_argument('--bundle',type=Path,required=True);args=parser.parse_args()
    print(json.dumps(predict_row(json.loads(args.features.read_text()),args.bundle),indent=2))
if __name__=='__main__': main()
