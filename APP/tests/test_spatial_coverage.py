"""Coverage must not contaminate measured labels or evaluation."""
import csv
import hashlib
import json
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'APP/desktop'))
from engine import Engine


class SpatialCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Engine(ROOT/'APP/prototype/runtime')
        script=(ROOT/'APP/prototype/data.js').read_text(encoding='utf-8')
        cls.districts=json.loads(script.split('=',1)[1].strip().rstrip(';'))['districts']

    def test_every_map_district_and_season_returns_estimate(self):
        count=0
        for district in self.districts:
            for season in self.engine.prep['categories'][1]:
                result=self.engine.predict_seasonal_yield({'districtId':district['id'],'season':season,
                    'areaHa':2,'landAreaHa':3,'averageTemperatureC':27})
                self.assertTrue(result['ok'],(district['name'],season,result))
                self.assertGreaterEqual(result['yieldTPerHa'],0)
                if result['referenceKind']=='synthetic_neighbour_transfer':
                    self.assertEqual(result['district'],district['name'])
                self.assertIsNone(result['observedYield'])
                self.assertFalse(result['testMetricsApplyToThisForecast'])
                self.assertTrue(all(year<=2020 for year in result['referenceYears']))
                count+=1
        self.assertEqual(count,515)

    def test_generated_data_is_traceable_train_only(self):
        coverage=self.engine.coverage
        source=ROOT/'DATASET/merged/rice_master.csv'
        self.assertEqual(hashlib.sha256(source.read_bytes()).hexdigest(),coverage['metadata']['source_master_sha256'])
        self.assertEqual(len(self.engine.history),2642)
        with (ROOT/'DATASET/candidates/spatial_coverage/synthetic_train.csv').open(newline='',encoding='utf-8') as handle:
            rows=list(csv.DictReader(handle))
        self.assertEqual(len(rows),3094)
        for row in rows:
            self.assertEqual(row['DATA_ORIGIN'],'synthetic_neighbour_transfer')
            self.assertLessEqual(int(row['FYEAR']),2020)
            keys=json.loads(row['DONOR_RECORD_KEYS']);weights=json.loads(row['DONOR_WEIGHTS'])
            self.assertAlmostEqual(sum(weights),1)
            donors=[self.engine.history[key] for key in keys]
            self.assertTrue(all(r['split']=='train' for r in donors))
            self.assertAlmostEqual(float(row['YIELD']),sum(w*r['observed'] for w,r in zip(weights,donors)))
            self.assertAlmostEqual(float(row['PRODUCTION_TONNES']),float(row['YIELD'])*float(row['CROP_AREA']))

    def test_fallback_disclosed_but_not_used_for_measured_pairs(self):
        known=next((key,row) for key,row in self.engine.history.items() if row['split']=='train')
        district,_,season=known[0].split('|')
        result=self.engine.predict_seasonal_yield({'districtId':district,'season':season,'areaHa':1,'averageTemperatureC':27})
        self.assertEqual(result['referenceKind'],'measured_training_reference')
        key=next(iter(self.engine.coverage['references']));district,season=key.split('|')
        result=self.engine.predict_seasonal_yield({'districtId':district,'season':season,'areaHa':1,'averageTemperatureC':27})
        self.assertEqual(result['referenceKind'],'synthetic_neighbour_transfer')
        self.assertTrue(result['neighbourReferences'])
        self.assertTrue(any('synthetic' in warning for warning in result['warnings']))
        bad=self.engine.predict_seasonal_yield({'districtId':'NOT_A_DISTRICT','season':season,'areaHa':1,'averageTemperatureC':27})
        self.assertFalse(bad['ok'])


if __name__=='__main__':unittest.main()
