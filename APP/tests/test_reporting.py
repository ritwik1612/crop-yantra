"""PDF content, image embedding, scenario arithmetic and stale-snapshot guards."""
import base64
import io
import json
import sys
import unittest
from pathlib import Path
from PIL import Image
from pypdf import PdfReader

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'APP/desktop'))
from reporting import ReportSession,build_pdf
from engine import Engine

class ReportingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Engine(ROOT/'APP/prototype/runtime')
        cls.session=ReportSession(cls.engine,ROOT/'APP/desktop/branding/paddy.png')
        key=next(k for k in cls.engine.history if '|2020|Kharif' in k)
        district=key.split('|')[0]
        cls.request={'districtId':district,'district':'Demo district','state':'Tamil Nadu','season':'Kharif',
          'areaHa':10,'landAreaHa':15,'averageTemperatureC':27,'seasonalRainfallMm':900}
        cls.result=cls.session.predict_seasonal_yield(cls.request)
        if not cls.result['ok']:raise AssertionError(cls.result)
        # Standalone class-result fixture, not a new claimed evaluation result.
        encoded=base64.b64encode((ROOT/'APP/prototype/assets/blast-real.jpg').read_bytes()).decode()
        cls.health=cls.session.classify_image(encoded)
        if not cls.health['ok']:raise AssertionError(cls.health)
        cls.options={'mode':'combined','yieldId':cls.result['exportId'],'healthId':cls.health['exportId'],
          'scenario':{'areaHa':12,'priceINRPerKg':20}}

    def test_combined_pdf(self):
        data=self.session.create(self.options);reader=PdfReader(io.BytesIO(data))
        self.assertEqual(len(reader.pages),4)
        content='\n'.join(p.extract_text() for p in reader.pages)
        self.assertIn('Yield prediction',content);self.assertIn('Rice photo screening',content)
        self.assertIn('Gross value',content);self.assertIn('12.00 ha',content)
        expected=f"{self.result['yieldTPerHa']*12*1000*20:,.2f}"
        self.assertIn(expected,content)
        self.assertTrue(reader.pages[2].images)
        for page in reader.pages:self.assertIn('PAGE ',page.extract_text())

    def test_single_reports(self):
        for mode in ('yield','health'):
            reader=PdfReader(io.BytesIO(self.session.create({**self.options,'mode':mode})))
            self.assertEqual(len(reader.pages),2)

    def test_stale_or_missing_results(self):
        for option in ({**self.options,'yieldId':'stale'},{**self.options,'healthId':'wrong'},{'mode':'health'}):
            with self.assertRaises(ValueError):self.session.create(option)

    def test_invalid_scenarios(self):
        for scenario in ({'areaHa':0},{'areaHa':float('nan')},{'areaHa':10,'priceINRPerKg':-1}):
            with self.assertRaises(ValueError):self.session.create({**self.options,'scenario':scenario})

if __name__=='__main__':unittest.main()
