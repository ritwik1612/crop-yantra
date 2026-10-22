"""State encoding and actual tree-path explanations must preserve predictions."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'APP/desktop'))
from engine import Engine

class ExplanationAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.engine=Engine(ROOT/'APP/prototype/runtime')

    def test_nellore_not_misidentified_as_other_state(self):
        r=self.engine.predict_seasonal_yield({'districtId':'IND.2.7_1','season':'Kharif','areaHa':12,'landAreaHa':15,'averageTemperatureC':27})
        self.assertTrue(r['ok'],r)
        self.assertEqual(r['sourceState'],'Andhra Pradesh')
        flags={v['state']:v for v in r['stateEncodingAudit']}
        self.assertEqual(flags['Andhra Pradesh']['input'],1)
        self.assertTrue(all(v['input']==0 for k,v in flags.items() if k!='Andhra Pradesh'))
        self.assertEqual(flags['Andhra Pradesh']['modelSplits'],0)
        self.assertEqual(flags['Telangana']['modelSplits'],0)
        self.assertNotEqual(flags['Karnataka']['contribution'],0)
        self.assertEqual(r['referenceKind'],'synthetic_neighbour_transfer')
        self.assertAlmostEqual(r['yieldTPerHa'],3.444624083014588)
        self.check_explanation(r)

    def check_explanation(self,r):
        self.assertAlmostEqual(r['baseline']+sum(v['contribution'] for v in r['contributions']),r['yieldTPerHa'])
        trace=r['treePathExample']
        self.assertAlmostEqual(trace['rootValue']+sum(s['change'] for s in trace['steps']),trace['leafValue'])
        for step in trace['steps']:
            self.assertAlmostEqual(step['after']-step['before'],step['change'])
            self.assertEqual(step['branch']=='left (≤)',step['input']<=step['threshold'])
        self.assertEqual(sum(v['input'] for v in r['stateEncodingAudit']),1)

    def test_each_measured_state_and_weather_scenario(self):
        for state in self.engine.prep['categories'][0]:
            key=next(k for k,v in self.engine.history.items() if v['state']==state and v['split']=='train' and k.endswith('|Kharif'))
            for temperature in (24,32):
                r=self.engine.predict_seasonal_yield({'districtId':key.split('|')[0],'season':'Kharif','areaHa':3,'averageTemperatureC':temperature,'seasonalRainfallMm':800})
                self.assertTrue(r['ok'],r);self.check_explanation(r)
                self.assertEqual(r['sourceState'],state)

if __name__=='__main__':unittest.main()
