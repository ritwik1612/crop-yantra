"""Shared, no-fitting preflight for yield and image training. Writes a readiness report."""
import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def run_check(script):
    result = subprocess.run([sys.executable, str(ROOT / script)], cwd=ROOT,
                            capture_output=True, text=True, check=False)
    if result.returncode:
        raise RuntimeError(f'{script} failed:\n{result.stderr or result.stdout}')
    return json.loads(result.stdout)


def check_yield():
    import numpy as np
    import pandas as pd
    import torch
    from APP.inference.preprocess import transform_rows
    from APP.models.tabular import YieldMLP, make_gbdt
    from APP.training.train import load_data

    report = run_check('APP/training/train.py')
    if report['missing_training_dependencies']:
        raise RuntimeError(f"Missing dependencies: {report['missing_training_dependencies']}")
    manifest, arms = load_data()
    master = pd.read_csv(ROOT / 'DATASET/merged/rice_master.csv')
    keys = ['IDREGION', 'FYEAR', 'SEASON']
    indexed = master.set_index(keys)
    if not indexed.index.is_unique:
        raise ValueError('Master contains duplicate observation keys')
    checks = {}
    torch.set_num_threads(2)
    for arm, parts in arms.items():
        differences = {}
        for split, part in parts.items():
            rows = indexed.loc[pd.MultiIndex.from_frame(part['frame'][keys])].reset_index()
            if not np.allclose(rows.YIELD, part['y'], rtol=1e-5, atol=1e-6):
                raise ValueError(f'{arm}/{split}: master targets do not match exports')
            output, _ = transform_rows(rows.to_dict('records'), arm)
            actual = output.to_numpy(dtype=np.float32)
            if not np.allclose(actual, part['x'], rtol=1e-5, atol=1e-5):
                raise ValueError(f'{arm}/{split}: saved preprocessing does not reproduce exported inputs')
            differences[split] = float(np.max(np.abs(actual - part['x'])))
        model = YieldMLP(len(manifest[arm]['predictor_columns'])).eval()
        batch = torch.tensor(parts['train']['x'][:8])
        with torch.inference_mode():
            prediction = model(batch)
        if list(prediction.shape) != [8] or not torch.isfinite(prediction).all():
            raise ValueError(f'{arm}: invalid MLP forward pass')
        tree = make_gbdt()
        if tree.get_params()['early_stopping']:
            raise ValueError('Tree early stopping must not make an implicit random holdout')
        checks[arm] = {'preprocessing_max_absolute_difference': differences,
                       'mlp_forward_shape': list(prediction.shape),
                       'tree_class': type(tree).__name__, 'tree_fitted': False}
    report['saved_preprocessing_reproduces_all_splits'] = True
    report['device'] = 'cpu'
    report['device_note'] = 'Small tabular experiments run on CPU; the image runner uses CUDA when available'
    report['model_checks'] = checks
    report['preprocessing_artifact_sha256'] = {
        name: hashlib.sha256((ROOT / 'pre-processing/artifacts' / name).read_bytes()).hexdigest()
        for name in ['standard_preprocessor.pkl', 'denoising_autoencoder.pt']
    }
    report['training_source'] = 'Original source-backed chronological exports; neighbour augmentation is not silently substituted'
    return report


def check_images():
    report = run_check('APP/training/images/train.py')
    inventory_file = ROOT / 'APP/training/images/dataset_inventory.json'
    if not inventory_file.exists():
        raise FileNotFoundError('Run APP/tools/record_image_dataset.py to verify the source archive')
    inventory = json.loads(inventory_file.read_text(encoding='utf8'))
    if inventory['manifest_sha256'] != report['manifest_sha256']:
        raise ValueError('Image inventory and current manifest disagree')
    report['selected_images'] = inventory['selected_images']
    report['prepared_total_bytes'] = inventory['prepared_total_bytes']
    report['source_archive_crc_record'] = inventory['archive_crc_check']
    report['source_archive_note'] = 'CRC was verified at acquisition; current preflight rechecks every selected photo SHA256'
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=['yield', 'images', 'both'], default='both')
    parser.add_argument('--output', type=Path, default=ROOT / 'APP/training/readiness.json')
    args = parser.parse_args()
    report = {'checked_utc': datetime.now(timezone.utc).isoformat(),
              'python': platform.python_version(), 'supervised_training_started': False,
              'task': args.task, 'checks': {}, 'errors': {}}
    try:
        import torch
        report['device'] = 'cuda' if torch.cuda.is_available() else 'cpu'
        report['packages'] = {name: importlib.metadata.version(name) for name in
                              ['torch', 'torchvision', 'numpy', 'pandas', 'scikit-learn', 'Pillow', 'ImageHash']}
    except Exception as error:
        report['errors']['environment'] = f'{type(error).__name__}: {error}'
    tasks = {'yield': check_yield, 'images': check_images}
    for name, function in tasks.items():
        if args.task not in ('both', name):
            continue
        print(f'Checking {name} without fitting...', flush=True)
        try:
            report['checks'][name] = function()
        except Exception as error:
            report['errors'][name] = f'{type(error).__name__}: {error}'
    report['status'] = 'ready' if not report['errors'] else 'not_ready'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + '\n', encoding='utf8')
    print(json.dumps(report, indent=2))
    if report['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
