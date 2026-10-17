"""Build a private, allowlisted Colab transfer bundle; never upload or train anything."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def collect_files(root=ROOT):
    required_files = [
        'APP/training/train.py', 'APP/training/check.py', 'APP/training/run.py',
        'APP/training/requirements.txt', 'APP/training/START_TRAINING.md',
        'APP/training/images/train.py', 'APP/training/images/prepare_data.py',
        'APP/training/images/requirements.txt', 'APP/training/images/dataset_inventory.json',
        'APP/models/tabular.py', 'APP/inference/preprocess.py', 'APP/inference/predict.py',
        'pre-processing/denoising_autoencoder.py',
        'pre-processing/artifacts/standard_preprocessor.pkl',
        'pre-processing/artifacts/denoising_autoencoder.pt',
        'DATASET/training/manifest.json', 'DATASET/merged/rice_master.csv',
        'DATASET/images/prepared/paddy_doctor_4class/manifest.json',
        'APP/models/pretrained/checkpoints/efficientnet_b0_rwightman-7f5810bc.pth',
    ]
    required_files += [f'DATASET/training/{arm}/{split}.csv'
                       for arm in ['standard', 'autoencoder'] for split in ['train', 'validation', 'test']]
    image_root = root / 'DATASET/images/prepared/paddy_doctor_4class'
    manifest = json.loads((image_root / 'manifest.json').read_text(encoding='utf8'))
    for row in manifest['images']:
        image = (image_root / row['path']).resolve()
        if not image.is_relative_to(image_root.resolve()):
            raise ValueError('Image path escapes the prepared subset')
        required_files.append(image.relative_to(root.resolve()).as_posix())
    files = sorted(set(required_files))
    for name in files:
        path = root / name
        if not path.is_file() or path.is_symlink():
            raise ValueError(f'Missing or unsupported bundle file: {name}')
    return files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'OTHER/training_transfer/crop_yantra_training.zip')
    args = parser.parse_args()
    files = collect_files()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    hashes = {}
    # Exclusive creation protects an existing transfer bundle from replacement.
    with zipfile.ZipFile(args.output, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=1) as bundle:
        for name in files:
            data = (ROOT / name).read_bytes()
            bundle.writestr(name, data)
            hashes[name] = hashlib.sha256(data).hexdigest()
        bundle.writestr('TRANSFER_MANIFEST.json', json.dumps({'schema_version': 1,
            'purpose': 'Private training transfer; not a redistributable image dataset',
            'files': hashes, 'credentials_included': False}, indent=2))
    with zipfile.ZipFile(args.output) as bundle:
        if bundle.testzip():
            raise ValueError('Transfer ZIP CRC verification failed')
    print(json.dumps({'bundle': str(args.output), 'files': len(files),
        'bytes': args.output.stat().st_size, 'uploaded': False, 'training_started': False}, indent=2))


if __name__ == '__main__':
    main()
