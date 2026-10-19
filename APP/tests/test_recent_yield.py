"""Recent cohort, portable-runtime and current-scenario regression checks."""
import csv
import json
import sys
import unittest
from collections import Counter
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'APP/desktop'))
from engine import Engine
from APP.training.train import metrics


class RecentYieldTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Engine(ROOT/'APP/prototype/runtime')
        cls.bundle=json.loads((ROOT/'APP/training/runs/recent_yield_20261019/bundle.json').read_text())

    def test_source_units_and_recent_labels(self):
        provenance=json.loads((ROOT/'DATASET/raw/government/upag/provenance.json').read_text())
        self.assertEqual(provenance['units']['yield'],'Kg per Hectare')
        self.assertEqual(provenance['four_state_rice_rows'],2815)
        with (ROOT/'DATASET/merged/rice_master.csv').open(newline='',encoding='utf-8') as f:rows=list(csv.DictReader(f))
        self.assertEqual(len(rows),2642)
        self.assertEqual(max(int(r['FYEAR']) for r in rows),2024)
        self.assertEqual(len({(r['IDREGION'],r['FYEAR'],r['SEASON']) for r in rows}),len(rows))
        for r in rows:
            self.assertAlmostEqual(float(r['YIELD']),float(r['PRODUCTION_TONNES'])/float(r['CROP_AREA']))
            if r['SEASON']=='Summer':self.assertEqual(int(r['WEATHER_DAY_COUNT']),122)
            if r['SEASON']=='Rabi':self.assertIn(int(r['WEATHER_DAY_COUNT']),(181,182))

    def test_every_held_out_runtime_prediction_reproduces_metrics(self):
        for kind,expected_key in [('gbdt','tree_metrics'),('mlp','metrics')]:
            actual=[];target=[]
            for key,row in self.engine.history.items():
                if row['split']!='test':continue
                district,year,season=key.split('|')
                result=self.engine.predict_yield({'districtId':district,'year':int(year),'season':season,'areaHa':12,'proposedModel':kind})
                self.assertTrue(result['ok'],result);actual.append(result['yieldTPerHa']);target.append(row['observed'])
            self.assertEqual(len(actual),337)
            measured=metrics(np.asarray(target),np.asarray(actual))
            for name,value in self.bundle[expected_key]['test'].items():self.assertAlmostEqual(measured[name],value,places=5)

    def test_all_supported_training_references_accept_temperature_scenarios(self):
        pairs={(k.split('|')[0],k.split('|')[2]) for k,r in self.engine.history.items() if r['split']=='train'}
        for district,season in pairs:
            for temp in (24,30):
                result=self.engine.predict_seasonal_yield({'districtId':district,'season':season,'areaHa':1,'averageTemperatureC':temp,'proposedModel':'gbdt'})
                self.assertTrue(result['ok'],result)
                self.assertGreaterEqual(result['yieldTPerHa'],0)
                self.assertTrue(all(y<=2020 for y in result['referenceYears']))
        self.assertEqual(self.engine.meta['yield_default_model'],'gbdt')


if __name__=='__main__':unittest.main()
