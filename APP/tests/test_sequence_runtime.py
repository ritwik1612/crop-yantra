"""Neural-only runtime, map coverage, input validation and deployment parity."""
import json
import base64
import sys
import unittest
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'APP/desktop'))
from engine import Engine


class SequenceRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine=Engine(ROOT/'APP/prototype/runtime')
        cls.request={'districtId':'IND.2.7_1','season':'Kharif','areaHa':12,
                     'landAreaHa':15,'averageTemperatureC':27}

    def test_no_tree_in_active_route(self):
        self.assertIsNone(self.engine.trees)
        self.assertIsNone(self.engine.coverage)
        self.assertEqual(self.engine.status()['yieldDefaultModel'],'cnn_lstm')
        self.assertFalse(self.engine.predict_yield({'year':2019})['ok'])

    def test_all_map_reference_scenarios(self):
        for key in self.engine.sequence.references:
            gid,season=key.split('|')
            result=self.engine.predict_seasonal_yield({**self.request,'districtId':gid,'season':season})
            self.assertTrue(result['ok'],(key,result))
            self.assertEqual(result['modelKind'],'cnn_lstm')
            self.assertTrue(np.isfinite(result['yieldTPerHa']))
            self.assertAlmostEqual(result['productionTonnes'],result['yieldTPerHa']*12)

    def test_validation_and_inputs(self):
        for updates in [{'areaHa':0},{'areaHa':20},{'landAreaHa':True},
                        {'averageTemperatureC':float('nan')},{'year':2026},{'season':'Whole Year'},
                        {'seasonalRainfallMm':-1},{'relativeHumidityPct':101}]:
            self.assertFalse(self.engine.predict_seasonal_yield({**self.request,**updates})['ok'],updates)
        result=self.engine.predict_seasonal_yield(self.request)
        changed=self.engine.predict_seasonal_yield({**self.request,'averageTemperatureC':30})
        self.assertNotEqual(result['yieldTPerHa'],changed['yieldTPerHa'])
        doubled=self.engine.predict_seasonal_yield({**self.request,'areaHa':24,'landAreaHa':30})
        self.assertEqual(result['yieldTPerHa'],doubled['yieldTPerHa'])
        self.assertAlmostEqual(result['productionTonnes']*2,doubled['productionTonnes'])

    def test_target_state_and_cutoff(self):
        r=self.engine.predict_seasonal_yield(self.request)
        flags={v['name']:v['value'] for v in r['sequence']['staticFeatures']}
        self.assertEqual(flags['STATE_Andhra Pradesh'],1)
        self.assertEqual(flags['STATE_Karnataka'],0)
        self.assertEqual(r['sequence']['leadDays'],60)
        self.assertEqual(r['referenceKind'],'synthetic_neighbour_transfer')
        self.assertIsNone(r['baseline'])
        self.assertIn('occlusion',r['explanationMethod'])
        self.assertEqual(len(r['contributions']),13)
        self.assertEqual(len(r['networkTrace']['joined']),43)
        self.assertEqual(len(r['networkTrace']['dense']),64)
        self.assertEqual(len(r['networkTrace']['lstmStates']),r['sequence']['steps'])
        np.testing.assert_allclose(r['networkTrace']['joined'][:32],r['networkTrace']['lstmStates'][-1])

    def test_frozen_test_runtime_parity(self):
        data=dict(np.load(ROOT/'DATASET/training/sequences_lead60/test.npz'))
        config=self.engine.sequence.config
        output=self.engine.sequence.session.run(None,{k:data[k] for k in ['weather','lengths','static']})[0]
        import csv
        with (ROOT/'APP/training/runs/sequences_20261023_cpu/selected_test_predictions.csv').open() as f:
            original=np.array([float(r['predicted_yield_t_ha']) for r in csv.DictReader(f)])
        self.assertLess(float(np.max(np.abs(output-original))),2e-5)
        self.assertAlmostEqual(float(np.abs(output-data['yield_t_ha']).mean()),config['test']['MAE'],places=5)

    def test_image_stage_trace(self):
        photo=base64.b64encode((ROOT/'APP/prototype/assets/brown-spot-real.jpg').read_bytes()).decode()
        result=self.engine.classify_image(photo)
        self.assertTrue(result['ok'])
        trace=result['imageTrace']
        self.assertEqual(len(trace['stages']),9)
        self.assertEqual(trace['inputShape'],[1,3,224,224])
        self.assertEqual(trace['stages'][-1]['outputShape'],[1,1280,7,7])
        self.assertEqual(len(trace['pooled']),1280)
        self.assertTrue(trace['crop'].startswith('data:image/png;base64,'))
        self.assertAlmostEqual(sum(r['score'] for r in result['scores']),1,places=5)


if __name__=='__main__':unittest.main()
