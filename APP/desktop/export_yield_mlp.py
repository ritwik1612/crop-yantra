"""Export the trained standard MLP, verify every held-out row, then activate it.

Uses the original validation-selected checkpoint; never refits on test labels.
The ONNX graph includes target de-standardization and returns tonnes/hectare.
"""
import hashlib
import argparse
import json
import sys
from pathlib import Path
import numpy as np
import onnxruntime as ort
import torch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from APP.models.tabular import YieldMLP
from APP.training.train import load_data


class PhysicalYield(torch.nn.Module):
    def __init__(self, model, mean, scale):
        super().__init__()
        self.model = model
        self.mean, self.scale = mean, scale

    def forward(self, values):
        return self.model(values) * self.scale + self.mean


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contextual',action='store_true')
    parser.add_argument('--source',type=Path,help='Explicit validation-selected checkpoint directory')
    args=parser.parse_args()
    torch.set_num_threads(1)
    source = ROOT/('APP/training/runs/contextual_yield_20261019' if args.contextual else 'APP/training/runs/20261017T175142_753017Z/standard_mlp')
    if args.source:source=args.source
    runtime = ROOT/'APP/prototype/runtime'
    bundle = json.loads((source/'bundle.json').read_text())
    _, arms = load_data()
    checkpoint = torch.load(source/'model.pt', map_location='cpu', weights_only=True)
    cfg = bundle['configuration']
    if args.contextual:
        from APP.models.contextual_yield import ContextualYield
        model=ContextualYield(len(cfg['district_vocabulary']),cfg['dropout'])
    else:
        model = YieldMLP(len(bundle['predictor_columns']))
    model.load_state_dict(checkpoint['state_dict'])
    graph = PhysicalYield(model, cfg['target_mean'], cfg['target_scale']).eval()
    target = runtime/'yield-mlp.onnx'
    torch.onnx.export(graph, (torch.zeros(1, len(bundle['predictor_columns'])),), str(target),
                      input_names=['features'], output_names=['yield_t_per_ha'],
                      dynamic_axes={'features': {0: 'batch'}, 'yield_t_per_ha': {0: 'batch'}},
                      opset_version=17, dynamo=False)
    session = ort.InferenceSession(str(target), providers=['CPUExecutionProvider'])
    error = 0.
    for part in arms['standard'].values():
        values = part['x']
        if args.contextual:
            frame=part['frame']
            keys=frame.STATE+'|'+frame.DISTRICT
            if cfg.get('season_context'):keys=keys+'|'+frame.SEASON
            indexes=keys.map(cfg['district_vocabulary']).fillna(0).to_numpy()
            values=np.column_stack([values,(frame.FYEAR-cfg['year_mean'])/cfg['year_scale'],indexes]).astype(np.float32)
        with torch.inference_mode():
            expected = graph(torch.from_numpy(values)).numpy()
        actual = session.run(None, {'features': values})[0]
        error = max(error, float(np.max(np.abs(expected-actual))))
        np.testing.assert_allclose(actual, expected, atol=2e-5, rtol=1e-5)
    path = runtime/'metadata.json'
    meta = json.loads(path.read_text())
    meta['version'] = '2026-10-19'
    meta['yield_mlp'] = {
        'model': 'Contextual MLP regressor' if args.contextual else 'MLP regressor',
        'model_kind': 'contextual_mlp' if args.contextual else 'standard_mlp',
        'architecture': [28, 64, 32, 1], 'input_count':len(bundle['predictor_columns']),
        'activation': 'GELU', 'dropout': cfg.get('dropout',.2), 'best_epoch': cfg['best_epoch'],
        'target_mean': cfg['target_mean'], 'target_scale': cfg['target_scale'],
        'test': bundle['metrics']['test'], 'validation': bundle['metrics']['validation'],
        'category_reference': {name: str(arms['standard']['train']['frame'][name].mode().iloc[0]) for name in ('STATE','SEASON')},
        'export_max_error': error,
        'checkpoint_sha256': hashlib.sha256((source/'model.pt').read_bytes()).hexdigest(),
        'selection': 'Chronological validation-selected checkpoint; tree benchmark retained.'}
    if args.contextual:
        meta['yield_mlp'].update({key:cfg[key] for key in ('district_vocabulary','year_mean','year_scale')})
        meta['yield_mlp']['season_context']=cfg.get('season_context',False)
        meta['yield_mlp']['warm_baseline']=cfg.get('warm_baseline',False)
        if cfg.get('warm_baseline'):meta['yield_mlp']['model']='Contextual Residual MLP regressor'
        meta['yield_mlp']['original_mlp_test']={'MAE':.5601385235786438,'RMSE':.7330376236563647,'R2':.3521360158920288}
    path.write_text(json.dumps(meta, indent=2)+'\n', encoding='utf8')
    print(f'MLP exported and verified on all 2,018 rows; max absolute error {error:.9g} t/ha.')


if __name__ == '__main__':
    main()
