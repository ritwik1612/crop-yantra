"""Export existing trained weights for inference; never fits or retrains a model."""
import json
import pickle
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
import torch
from torch import nn
from torchvision.models import efficientnet_b0
from torchvision.models import EfficientNet_B0_Weights
import onnxruntime as ort

ROOT = Path(__file__).resolve().parents[2]
DEST = ROOT / 'APP/prototype/runtime'

def save(name, value):
    (DEST/name).write_text(json.dumps(value, allow_nan=False, separators=(',', ':')), encoding='utf8')

def main():
    torch.set_num_threads(2)
    DEST.mkdir(exist_ok=True)
    run = ROOT/'APP/training/runs/20261017T175142_753017Z/standard_gbdt'
    with (run/'model.pkl').open('rb') as stream:
        model = pickle.load(stream)
    with (ROOT/'pre-processing/artifacts/standard_preprocessor.pkl').open('rb') as stream:
        prep = pickle.load(stream)
    numeric = list(prep.transformers_[0][2])
    pipe = prep.named_transformers_['numeric']
    print('Preprocessor steps:', list(pipe.named_steps), flush=True)
    imputer, scaler = list(pipe.named_steps.values())
    encoder = prep.named_transformers_['categorical']
    if hasattr(encoder, 'named_steps'):
        encoder = list(encoder.named_steps.values())[-1]
    config = {'numeric': numeric, 'median': imputer.statistics_.tolist(),
              'mean': scaler.mean_.tolist(), 'scale': scaler.scale_.tolist(),
              'categories': [list(c) for c in encoder.categories_],
              'predictors': list(prep.get_feature_names_out())}
    master = pd.read_csv(ROOT/'DATASET/merged/rice_master.csv')
    cols = numeric + ['STATE', 'SEASON']
    x = np.asarray(prep.transform(master[cols]), dtype=np.float64)
    # Portable exact tree traversal avoids a large sklearn server dependency.
    trees = []
    for iteration in model._predictors:
        for tree in iteration:
            if tree.nodes['is_categorical'].any():
                raise ValueError('Categorical tree splits need a different exporter')
            portable = [[float(n['value']), int(n['feature_idx']), float(n['num_threshold']),
                         int(n['left']), int(n['right']), bool(n['is_leaf']),
                         bool(n['missing_go_to_left'])] for n in tree.nodes]
            # Explain paths using training-cover-weighted expected leaf outputs.
            # sklearn's stored internal Newton values are not shrinkage-scaled
            # leaf predictions and must not be used directly as attributions.
            for index in reversed(range(len(portable))):
                node = portable[index]
                if not node[5]:
                    left,right = node[3:5]
                    a,b = int(tree.nodes[left]['count']),int(tree.nodes[right]['count'])
                    node[0] = (portable[left][0]*a+portable[right][0]*b)/(a+b)
            trees.append(portable)
    tree_data = {'baseline': float(model._baseline_prediction[0, 0]), 'trees': trees}
    def score(row):
        result = tree_data['baseline']
        for tree in trees:
            index = 0
            while not tree[index][5]:
                node = tree[index]; value = row[node[1]]
                left = node[6] if np.isnan(value) else value <= node[2]
                index = node[3] if left else node[4]
            result += tree[index][0]
        return result
    exported = np.array([score(row) for row in x])
    options = ort.SessionOptions(); options.intra_op_num_threads = 1
    error = float(np.max(np.abs(exported-model.predict(x))))
    if error > 1e-4:
        raise RuntimeError(f'Yield export parity failed: {error}')
    # Every served input has a source-backed exact district/year/season match.
    # Labels are retained solely for comparisons, never included in model inputs.
    boundaries = pd.read_csv(ROOT/'DATASET/raw/boundaries/india_districts.csv')
    coordinate_ids = {}
    for _, boundary in boundaries.iterrows():
        coordinate = (round(float(boundary.CENTROID_X),6),round(float(boundary.CENTROID_Y),6))
        if coordinate in coordinate_ids:
            raise ValueError('Ambiguous boundary coordinates')
        coordinate_ids[coordinate] = boundary.GID_2
    records = {}
    for _, row in master.iterrows():
        # The map uses GADM IDs, whereas the source master uses normalized names.
        # Match by preserved representative coordinates exactly as build_ui_data.py.
        coordinate = (round(float(row.CENTROID_X),6),round(float(row.CENTROID_Y),6))
        gid = coordinate_ids[coordinate]
        key = f"{gid}|{int(row.FYEAR)}|{row.SEASON}"
        if key in records:
            raise ValueError('Ambiguous historical feature key')
        records[key] = {'numeric': [None if pd.isna(row[c]) else float(row[c]) for c in numeric],
                        'state': row.STATE, 'district': row.DISTRICT,
                        'observed': float(row.YIELD),
                        'split': 'train' if row.FYEAR <= 2015 else 'validation' if row.FYEAR <= 2017 else 'test'}
    save('preprocessor.json', config)
    save('yield.json', tree_data)
    save('historical.json', records)
    checkpoint = ROOT/'APP/training/runs/images_20261017T175203_027881Z/model.pt'
    ckpt = torch.load(checkpoint, map_location='cpu', weights_only=True)
    image = efficientnet_b0(weights=None)
    image.classifier[-1] = nn.Linear(image.classifier[-1].in_features, 4)
    image.load_state_dict(ckpt['state_dict']); image.eval()
    sample = torch.randn(1, 3, 224, 224)
    torch.onnx.export(image, sample, str(DEST/'rice.onnx'), input_names=['image'],
                      output_names=['logits'], opset_version=17, dynamo=False)
    session = ort.InferenceSession(str(DEST/'rice.onnx'), options, providers=['CPUExecutionProvider'])
    image_error = float(np.max(np.abs(session.run(None, {'image': sample.numpy()})[0]-image(sample).detach().numpy())))
    if image_error > 1e-4:
        raise RuntimeError(f'Image export parity failed: {image_error}')
    # Also check actual photos and the exact training evaluation transform.
    manifest = json.loads((ROOT/'DATASET/images/prepared/paddy_doctor_4class/manifest.json').read_text())
    from PIL import Image, ImageOps
    from torchvision.transforms import functional as F
    transform = EfficientNet_B0_Weights.IMAGENET1K_V1.transforms()
    for label in ckpt['classes']:
        row = next(r for r in manifest['images'] if r['split']=='validation' and r['class']==label)
        with Image.open(ROOT/'DATASET/images/prepared/paddy_doctor_4class'/row['path']) as photo:
            photo = ImageOps.exif_transpose(photo).convert('RGB')
            tensor = transform(photo).unsqueeze(0)
        with torch.inference_mode():
            original = image(tensor).numpy()
        converted = session.run(None, {'image': tensor.numpy()})[0]
        np.testing.assert_allclose(original, converted, atol=1e-4, rtol=1e-4)
    save('metadata.json', {'version': '2026-10-17', 'classes': ckpt['classes'],
        'yield_model': 'HistGradientBoostingRegressor', 'image_model': 'EfficientNet-B0',
        'yield_test': json.loads((run/'bundle.json').read_text())['metrics']['test'],
        'image_test_accuracy': .8625, 'image_test_macro_f1': .8635908732,
        'yield_export_max_error': error, 'image_export_max_error': image_error,
        'image_abstention_threshold': .65,
        'threshold_note': 'Conservative UI heuristic, not a calibrated diagnostic threshold',
        'source_checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest()})
    print(f'Export verified: yield max error {error:.8f}, image max error {image_error:.8f}; 4 real-photo parity checks passed.')

if __name__ == '__main__':
    main()
