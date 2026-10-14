"""Reuse trusted fitted transforms for a complete master-schema input row.

Not a weather service. UI fields alone cannot supply these features.
"""
import json
import pickle
import sys
from pathlib import Path
import numpy as np
import pandas as pd
import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'pre-processing'))
from denoising_autoencoder import DenoisingAutoencoder

def transform_rows(rows,representation,root=ROOT):
    manifest=json.loads((root/'DATASET/training/manifest.json').read_text())
    if representation not in ('standard','autoencoder'): raise ValueError('Unknown representation')
    frame=pd.DataFrame(rows)
    with (root/'pre-processing/artifacts/standard_preprocessor.pkl').open('rb') as handle: standard=pickle.load(handle)
    required=list(standard.feature_names_in_)
    missing=set(required)-set(frame.columns)
    if missing: raise ValueError(f'Missing input features: {sorted(missing)}. Location and area alone are insufficient.')
    numeric=[n for n in required if n not in ('STATE','SEASON')]
    for name in numeric:
        frame[name]=pd.to_numeric(frame[name],errors='raise')
        if np.isinf(frame[name].to_numpy(dtype=float)).any(): raise ValueError(f'Infinite input: {name}')
    if frame[['STATE','SEASON']].isna().any().any(): raise ValueError('State and season required')
    if representation=='standard':
        output=pd.DataFrame(standard.transform(frame[required]),columns=standard.get_feature_names_out())
    else:
        checkpoint=torch.load(root/'pre-processing/artifacts/denoising_autoencoder.pt',map_location='cpu',weights_only=False)
        x=checkpoint['numeric_preprocessor'].transform(frame[checkpoint['numeric_features']])
        model=DenoisingAutoencoder(len(checkpoint['numeric_features']),checkpoint['latent_dim'],checkpoint['dropout'])
        model.load_state_dict(checkpoint['model_state_dict']);model.eval()
        with torch.no_grad(): reconstruction,latent=model(torch.tensor(x,dtype=torch.float32))
        output=pd.DataFrame(latent.numpy(),columns=[f'AE_LATENT_{i:02d}' for i in range(1,checkpoint['latent_dim']+1)])
        categories=checkpoint['categorical_preprocessor']
        encoded=pd.DataFrame(categories.transform(frame[['STATE','SEASON']]),columns=categories.get_feature_names_out())
        output=pd.concat([output,encoded],axis=1)
        output['AE_RECONSTRUCTION_MSE']=((x-reconstruction.numpy())**2).mean(axis=1)
    output=output[manifest[representation]['predictor_columns']]
    if not np.isfinite(output.to_numpy()).all(): raise ValueError('Nonfinite preprocessed inputs')
    warnings=[]
    if not frame.STATE.isin(['Andhra Pradesh','Karnataka','Tamil Nadu','Telangana']).all(): warnings.append('State outside fitted cohort; extrapolation not established')
    if not frame.SEASON.isin(['Kharif','Rabi','Summer']).all(): warnings.append('Season unseen at fitting; encoded as all-zero indicators')
    return output,warnings
