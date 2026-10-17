"""Safety/packaging tests; never train on the project datasets."""
import json
import subprocess
from pathlib import Path
import pytest
from APP.training import check, package, run

ROOT = Path(__file__).resolve().parents[2]


def test_launcher_defaults_to_checks(monkeypatch):
    calls = []
    monkeypatch.setattr(run.sys, 'argv', ['run.py'])
    monkeypatch.setattr(run.subprocess, 'run', lambda command, **kwargs: calls.append(command))
    run.main()
    assert len(calls) == 1
    assert '--train' not in calls[0]
    assert calls[0][-2:] == ['--task', 'both']


def test_explicit_both_dispatches_two_runs_after_preflight(monkeypatch):
    calls = []
    monkeypatch.setattr(run.sys, 'argv', ['run.py', '--task', 'both', '--train'])
    monkeypatch.setattr(run.subprocess, 'run', lambda command, **kwargs: calls.append(command))
    run.main()
    assert len(calls) == 3
    assert '--train' not in calls[0]
    assert calls[1][1] == 'APP/training/train.py'
    assert calls[2][1] == 'APP/training/images/train.py'
    assert all('--train' in command for command in calls[1:])


def test_failed_preflight_never_dispatches_training(monkeypatch):
    calls = []
    def fail(command, **kwargs):
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)
    monkeypatch.setattr(run.sys, 'argv', ['run.py', '--train'])
    monkeypatch.setattr(run.subprocess, 'run', fail)
    with pytest.raises(subprocess.CalledProcessError):
        run.main()
    assert len(calls) == 1 and '--train' not in calls[0]


def test_preflight_reports_failure_not_ready(monkeypatch, tmp_path):
    output = tmp_path / 'readiness.json'
    def fail():
        raise ValueError('test incompatible preprocessing')
    monkeypatch.setattr(check, 'check_yield', fail)
    monkeypatch.setattr(check, 'check_images', lambda: {'status': 'image_data_ready'})
    monkeypatch.setattr(check.sys, 'argv', ['check.py', '--output', str(output)])
    with pytest.raises(SystemExit) as error:
        check.main()
    report = json.loads(output.read_text())
    assert error.value.code == 1
    assert report['status'] == 'not_ready'
    assert not report['supervised_training_started']
    assert 'yield' in report['errors']


def test_transfer_allowlist_has_no_raw_archives_or_credentials():
    names = package.collect_files()
    assert len([name for name in names if '/images/' in name and name.endswith('.jpg')]) == 1600
    assert 'pre-processing/artifacts/standard_preprocessor.pkl' in names
    assert all(not name.startswith(('OTHER/', 'github/', 'DATASET/images/source/')) for name in names)
    assert all(Path(name).name not in ('.env', 'kaggle.json', 'access_token', 'refresh_token') for name in names)


def test_notebook_code_valid_and_training_disabled():
    notebook = json.loads((ROOT / 'APP/training/Train_Both.ipynb').read_text(encoding='utf8'))
    code = [''.join(cell['source']) for cell in notebook['cells'] if cell['cell_type'] == 'code']
    for i, source in enumerate(code):
        compile(source, f'cell_{i}', 'exec')
    assert any('TRAIN_YIELD = False' in source and 'TRAIN_IMAGES = False' in source for source in code)
    assert all(cell.get('outputs', []) == [] for cell in notebook['cells'])
