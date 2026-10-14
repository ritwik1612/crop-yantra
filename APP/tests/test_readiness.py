"""Run with python -m unittest discover -s APP/tests; no yield model is fitted."""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('training_runner',ROOT/'APP/training/train.py')
runner=importlib.util.module_from_spec(spec);spec.loader.exec_module(runner)

class ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.manifest,cls.arms=runner.load_data()

    def test_schema(self):
        self.assertEqual(len(self.manifest['standard']['predictor_columns']),28)
        self.assertEqual(len(self.manifest['autoencoder']['predictor_columns']),16)
        self.assertEqual(self.manifest['target'],'YIELD')

    def test_partition_counts(self):
        for arm in self.arms.values():
            self.assertEqual([len(arm[s]['y']) for s in ('train','validation','test')],[1485,245,288])

    def test_map_and_observation_export(self):
        text=(ROOT/'APP/prototype/data.js').read_text(encoding='utf-8')
        data=json.loads(text.removeprefix('window.RYP_DATA = ').strip().removesuffix(';'))
        ids=[d['id'] for d in data['districts']]
        self.assertEqual(len(ids),len(set(ids)))
        self.assertEqual(len(ids),103)
        self.assertEqual(sum(d['records'] for d in data['districts']),2018)
        self.assertEqual(len(data['stateShapes']),6)
        self.assertTrue(all(d['path'].startswith('M') for d in data['districts']))
        for d in data['districts']:
            self.assertEqual(len(data['history'][d['id']]),d['records'])
            if d['state'] in ('Kerala','Puducherry'): self.assertEqual(d['records'],0)

if __name__=='__main__': unittest.main()
