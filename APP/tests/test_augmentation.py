"""Independent CSV/provenance checks; no fitted model required."""
import csv
import hashlib
import json
import math
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        return reader.fieldnames, list(reader)

def key(row):
    return '|'.join(row[name] for name in ('IDREGION', 'FYEAR', 'SEASON'))

class AugmentationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.headers, cls.original = read(ROOT/'DATASET/merged/rice_master.csv')
        cls.new_headers, cls.output = read(ROOT/'DATASET/augmented/rice_master_augmented.csv')
        cls.manifest = json.loads((ROOT/'DATASET/augmented/generation_manifest.json').read_text())
        cls.base = {key(row): row for row in cls.original}
        cls.mixed = {key(row): row for row in cls.output}

    def test_source_and_schema_preserved(self):
        self.assertEqual(self.headers, self.new_headers)
        self.assertEqual(len(self.new_headers), 30)
        self.assertEqual(len(self.output), 3363)
        self.assertEqual(len(self.mixed), len(self.output))
        for record_key, row in self.base.items():
            self.assertEqual(row, self.mixed[record_key])
        self.assertEqual(hashlib.sha256((ROOT/'DATASET/merged/rice_master.csv').read_bytes()).hexdigest(), self.manifest['source_sha256'])
        self.assertEqual(hashlib.sha256((ROOT/'DATASET/augmented/rice_master_augmented.csv').read_bytes()).hexdigest(), self.manifest['output_sha256'])

    def test_donors_and_calculations(self):
        generated = self.manifest['generated_records']
        self.assertEqual(len(generated), 1345)
        for entry in generated:
            target = self.mixed[entry['record_key']]
            self.assertLessEqual(int(target['FYEAR']), 2015)
            self.assertEqual(len(entry['donors']), 3)
            self.assertEqual(len({d['gid'] for d in entry['donors']}), 3)
            self.assertAlmostEqual(sum(d['weight'] for d in entry['donors']), 1, places=12)
            expected = 0
            for donor in entry['donors']:
                source = self.base[donor['record_key']]
                self.assertEqual(source['FYEAR'], target['FYEAR'])
                self.assertEqual(source['SEASON'], target['SEASON'])
                self.assertLessEqual(donor['distance_km'], 250.000001)
                expected += float(source['YIELD'])*donor['weight']
            self.assertAlmostEqual(float(target['YIELD']), expected, delta=0.000001)
            self.assertAlmostEqual(float(target['PRODUCTION_TONNES']), float(target['YIELD'])*float(target['CROP_AREA']), delta=0.000001)
            self.assertAlmostEqual(float(target['CROP_AREA_LOG1P']), math.log1p(float(target['CROP_AREA'])), delta=0.000001)
            self.assertEqual(target['AREA_FRACTION'], '')
            self.assertEqual(target['WEATHER_DAY_COUNT'], '')
            self.assertEqual(key(self.output[entry['csv_record_number']-1]), entry['record_key'])

    def test_historical_map_coverage(self):
        _, districts = read(ROOT/'DATASET/raw/boundaries/india_districts.csv')
        states = {'AndhraPradesh','Karnataka','TamilNadu','Telangana','Kerala','Puducherry'}
        coordinates = {(round(float(r['CENTROID_X']),6), round(float(r['CENTROID_Y']),6)) for r in self.output}
        targets = [r for r in districts if r['NAME_1'] in states]
        self.assertEqual(len(targets), 103)
        for row in targets:
            self.assertIn((round(float(row['CENTROID_X']),6),round(float(row['CENTROID_Y']),6)), coordinates)

if __name__ == '__main__':
    unittest.main()
