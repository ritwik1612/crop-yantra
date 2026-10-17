"""One entry point for both pipelines. No --train means preflight only."""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', choices=['yield', 'images', 'both'], default='both')
    parser.add_argument('--train', action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--yield-epochs', type=int, default=250)
    parser.add_argument('--image-epochs', type=int, default=15)
    parser.add_argument('--image-head-epochs', type=int, default=5)
    parser.add_argument('--image-batch-size', type=int, default=32)
    args = parser.parse_args()
    if min(args.yield_epochs, args.image_epochs, args.image_batch_size) < 1:
        parser.error('Epochs and batch size must be positive')
    if not 1 <= args.image_head_epochs <= args.image_epochs:
        parser.error('Image head epochs must be between 1 and image epochs')
    subprocess.run([sys.executable, str(ROOT / 'APP/training/check.py'), '--task', args.task], cwd=ROOT, check=True)
    if not args.train:
        print('Preflight complete. No supervised training started. Add --train only when intended.')
        return
    commands = []
    if args.task in ('yield', 'both'):
        commands.append(['APP/training/train.py', '--train', '--epochs', str(args.yield_epochs), '--seed', str(args.seed)])
    if args.task in ('images', 'both'):
        commands.append(['APP/training/images/train.py', '--train', '--epochs', str(args.image_epochs),
                         '--head-epochs', str(args.image_head_epochs), '--batch-size', str(args.image_batch_size), '--seed', str(args.seed)])
    for command in commands:
        subprocess.run([sys.executable, *command], cwd=ROOT, check=True)


if __name__ == '__main__':
    main()
