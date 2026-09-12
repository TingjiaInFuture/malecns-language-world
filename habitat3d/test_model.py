import copy
import json
import math
import os
from pathlib import Path
import tempfile
import time
import unittest
import numpy as np
from legacy_ecology import Habitat, DT, sector
from server import Runtime


class ModelTests(unittest.TestCase):
    def test_determinism_and_exact_resume(self):
        a,b=Habitat(42,3),Habitat(42,3)
        for _ in range(160):a.step();b.step()
        self.assertEqual(a.dump(),b.dump())
        c=Habitat.restore(json.loads(json.dumps(a.dump())))
        for _ in range(120):a.step();c.step()
        self.assertEqual(a.dump(),c.dump())

    def test_locality_and_no_hidden_coordinates(self):
        h=Habitat(7,2);a,b=h.flies;r=h.resources[1]
        a.update(x=r['x'],z=r['z']);b.update(x=0.,z=-7.)
        b['trust'][a['id']]=[1000.,1.]
        self.assertNotIn(r['id'],b['memory'])
        h.send(a,r)
        self.assertIsNotNone(b['hint'])
        self.assertFalse({'x','z','origin','resource_id'} & b['hint'].keys())
        self.assertEqual(b['hint']['sector'],sector(r['x'],r['z']))
        a.update(x=-20.,z=10.)
        with self.assertRaises(ValueError):h.send(a,r)
        a.update(x=-12.,z=9.);b.update(x=25.,z=10.);before=h.metrics['received'];h.send(a,h.resources[2])
        self.assertEqual(before,h.metrics['received'])

    def test_signal_investigation_and_contact_validation(self):
        h=Habitat(7,2);a,b=h.flies;r=h.resources[1]
        a.update(x=r['x'],z=r['z'],next_signal=9999.)
        b.update(x=0.,z=-7.,heading=math.pi/2,energy=.9,hydration=.15,fatigue=0.,next_signal=9999.)
        b['trust'][a['id']]=[1000.,1.]
        h.send(a,r);h.step()
        self.assertEqual(b['target']['source'],'signal')
        self.assertEqual(h.metrics['verified'],0)
        for _ in range(120):h.step()
        self.assertEqual(h.metrics['verified'],1)
        self.assertGreater(b['hydration'],.15)
        self.assertEqual(a['helped'],1)

    def test_false_hint_reduces_trust(self):
        h=Habitat(8,1);f=h.flies[0]
        f['hint']={'sender':'test','used':True,'word':'水','sector':'中央','id':99}
        h.resolve(f,False)
        self.assertEqual(h.metrics['verified'],0)
        self.assertEqual(h.metrics['failed'],1)
        self.assertEqual(f['trust']['test'],[2.,2.])

    def test_controls_and_strict_vocabulary(self):
        h=Habitat(3,2)
        self.assertEqual(h.human_message('水在东侧')['sector'],'东侧')
        for text in ['不要找水','水在哪里呢','hello','糖在月球']:
            with self.assertRaises(ValueError):h.human_message(text)
        h.control('communication',False);sent=h.metrics['sent']
        for _ in range(240):h.step()
        self.assertEqual(sent,h.metrics['sent'])
        for f in h.flies:
            self.assertIsNone(f['hint'])
            self.assertTrue((h.observation(f,h.perceive(f))[15:19]==0).all())
        with self.assertRaises(ValueError):h.human_message('找水')
        h.control('dry');self.assertTrue(all(r['amount']==0 for r in h.resources if r['kind']=='water'))
        h.control('rain');h.step();self.assertEqual(h.weather['rain'],.9)
        h.control('fruit');self.assertTrue(all(r['amount']==1 for r in h.resources if r['kind']=='food'))

    def test_independent_neural_state_and_frozen_gains(self):
        h=Habitat(6,3)
        for _ in range(240):h.step()
        self.assertEqual(h.brains.theta.shape,(3,1606))
        self.assertFalse(np.array_equal(h.brains.h[0],h.brains.h[1]))
        self.assertGreater(float(np.abs(h.brains.theta).max()),0)
        signs=np.sign(h.brains.base)
        self.assertTrue((signs==np.sign(h.brains.base*np.exp(h.brains.theta))).all())
        h.control('plasticity',False);before=h.brains.theta.copy()
        for _ in range(160):h.step()
        np.testing.assert_array_equal(before,h.brains.theta)
        broken=h.dump();broken['brains']['sha']='bad'
        with self.assertRaises(ValueError):Habitat.restore(broken)

    def test_runtime_save_archive_and_single_step(self):
        with tempfile.TemporaryDirectory() as d:
            r=Runtime(d,12,2,False)
            with self.assertRaises(ValueError):r.command({'action':'step'})
            r.command({'action':'pause','value':True});r.command({'action':'step'})
            self.assertEqual(r.world.t,DT)
            r.command({'action':'save'});s=Runtime(d,0,1,True)
            self.assertEqual(r.world.flies,s.world.flies)
            self.assertTrue(s.paused)
            r.command({'action':'reset','seed':20,'count':3})
            self.assertEqual(len(list(Path(d).glob('archive-*.json'))),1)
            self.assertEqual(r.world.count,3)

    def test_long_run_bounds(self):
        h=Habitat(20260913,12);start=time.perf_counter()
        for i in range(14400):
            h.step()
            if i%80==0:
                for f in h.flies:
                    self.assertTrue(np.isfinite([f[k] for k in ['x','y','z','energy','hydration','fatigue']]).all())
                    self.assertLessEqual((f['x']/27.5)**2+(f['z']/17.5)**2,1.000001)
                    for k in ['energy','hydration','fatigue']:self.assertTrue(0<=f[k]<=1)
                for r in h.resources:self.assertTrue(0<=r['amount']<=1)
        elapsed=time.perf_counter()-start
        report={'model_seconds':h.t,'ticks':h.tick,'wall_seconds':elapsed,'ms_per_tick':elapsed/14400*1000,
                'seed':h.seed,'alive':sum(f['alive'] for f in h.flies),'metrics':h.metrics,
                'mean_gain':float(np.abs(h.brains.theta).mean())}
        out=Path(os.environ.get('HABITAT_TEST_EVIDENCE',str(Path(__file__).parent/'evidence')));out.mkdir(parents=True,exist_ok=True)
        (out/'long_run.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        (out/'long_run_state.json').write_text(json.dumps(h.dump(),ensure_ascii=False),encoding='utf-8')
        self.assertEqual(h.t,3600.)


if __name__=='__main__':unittest.main(verbosity=2)
