"""Evaluation calculation and generated-artifact integrity checks; no training."""
import json
from pathlib import Path
import numpy as np
import pytest
from APP.evaluation.evaluate_models import digest, regression_metrics

ROOT=Path(__file__).resolve().parents[2]


def test_regression_units_and_thresholds():
    score=regression_metrics(np.array([1.,2.,3.,4.]),np.array([1.,2.5,4.,2.]))
    assert score['MAE']==pytest.approx(.875)
    assert score['within_0_5_t_ha_pct']==50
    assert score['within_1_t_ha_pct']==75
    assert score['mean_bias_t_ha']==pytest.approx(-.125)


@pytest.mark.skipif(not (ROOT/'docs/evaluation/2026-10-17/evaluation.json').exists(),reason='Local trained-model audit not generated')
def test_generated_audit_and_demo_preserve_model_contract():
    report=json.loads((ROOT/'docs/evaluation/2026-10-17/evaluation.json').read_text())
    assert report['no_retraining']
    assert report['yield']['overall_test']['rows']==288
    assert report['images']['overall_test']['photos']==240
    assert report['images']['overall_test']['accuracy']==pytest.approx(207/240)
    assert sum(g['rows'] for g in report['yield']['by_state'].values())==288
    assert all(v['photos']==240 for v in report['images']['conditions'].values())
    assert digest(ROOT/report['yield_run']/report['yield']['selected_experiment']/'model.pkl')==report['yield']['model_sha256']
    assert digest(ROOT/report['image_run']/'model.pt')==report['images']['model_sha256']
    folder=ROOT/'DATASET/images/testong images'
    demos=json.loads((folder/'demo_manifest.json').read_text())
    original=json.loads((ROOT/'DATASET/images/prepared/paddy_doctor_4class/manifest.json').read_text())
    train_ids={r['image_id'] for r in original['images'] if r['split']=='train'}
    assert len(demos)==40
    assert len({r['image_id'] for r in demos})==40
    assert sum(r['selection']=='seeded_class_sample' for r in demos)==32
    assert sum(r['selection']=='known_failure_example' for r in demos)==8
    for row in demos:
        assert row['image_id'] not in train_ids
        assert row['source_split']=='test' and row['season'] is None
        assert digest(folder/row['demo_path'])==row['sha256']
