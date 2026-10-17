"""Offline model and bridge contract checks; no report files or training."""
import base64
import io
import json
import sys
import unittest
from pathlib import Path
import numpy as np
from PIL import Image, ImageOps

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'APP/desktop'))
from engine import Engine

class DesktopTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Engine(ROOT/'APP/prototype/runtime')
        cls.key=next(k for k in cls.engine.history if '|2019|' in k)
    def request(self):
        district,year,season=self.key.split('|')
        return {'districtId':district,'year':int(year),'season':season,'areaHa':12}
    def test_yield_and_explanation_reconcile(self):
        r=self.engine.predict_yield(self.request())
        self.assertTrue(r['ok']);self.assertEqual(r['split'],'test')
        self.assertEqual(len(r['features']),21)
        self.assertEqual(len(r['encodedCategories']),7)
        self.assertAlmostEqual(r['productionTonnes'],r['yieldTPerHa']*12)
        self.assertAlmostEqual(r['baseline']+sum(v['contribution'] for v in r['contributions']),r['yieldTPerHa'])
    def test_user_area_does_not_change_yield(self):
        req=self.request();a=self.engine.predict_yield(req)
        req['areaHa']=24;b=self.engine.predict_yield(req)
        self.assertEqual(a['yieldTPerHa'],b['yieldTPerHa'])
        self.assertAlmostEqual(a['productionTonnes']*2,b['productionTonnes'])
    def test_missing_and_invalid_inputs(self):
        for override in [{'districtId':'unknown'},{'year':2026},{'areaHa':-1},{'areaHa':float('nan')},{'areaHa':True},{'year':2019.5}]:
            self.assertFalse(self.engine.predict_yield({**self.request(),**override})['ok'])
    def test_blank_and_invalid_photos(self):
        for color in ['white','black']:
            stream=io.BytesIO();Image.new('RGB',(256,256),color).save(stream,format='PNG')
            self.assertFalse(self.engine.classify_image(base64.b64encode(stream.getvalue()).decode())['ok'])
        self.assertFalse(self.engine.classify_image('not valid base64')['ok'])
    def test_real_photo_has_four_scores(self):
        manifest=json.loads((ROOT/'DATASET/images/prepared/paddy_doctor_4class/manifest.json').read_text())
        row=next(r for r in manifest['images'] if r['split']=='test' and r['class']=='normal')
        photo=(ROOT/'DATASET/images/prepared/paddy_doctor_4class'/row['path']).read_bytes()
        r=self.engine.classify_image(base64.b64encode(photo).decode())
        self.assertTrue(r['ok'],r)
        self.assertEqual(len(r['scores']),4)
        self.assertAlmostEqual(sum(v['score'] for v in r['scores']),1,places=5)
    def test_pixel_transform_matches_training(self):
        from torchvision.models import EfficientNet_B0_Weights
        transform=EfficientNet_B0_Weights.IMAGENET1K_V1.transforms()
        # Odd aspect ratios exercise resize/crop rounding, not only square inputs.
        rng=np.random.default_rng(42)
        for width,height in [(301,450),(600,333),(257,257)]:
            photo=Image.fromarray(rng.integers(0,256,(height,width,3),dtype=np.uint8))
            expected=transform(photo).numpy()[None]
            np.testing.assert_allclose(self.engine.image_tensor(photo),expected,atol=1e-6)

if __name__=='__main__': unittest.main()
