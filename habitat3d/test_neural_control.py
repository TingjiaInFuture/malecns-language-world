import copy
import json
import math
import unittest
import numpy as np
from ecology import Habitat,DT,height

class NeuralControlTests(unittest.TestCase):
    def world(self,n=2):return Habitat(42,n,'mbon')
    def test_zero_output_cannot_choose_move_eat_or_signal(self):
        h=self.world();f=h.flies[0];r=h.resources[0]
        f.update(x=r['x'],z=r['z'],y=height(r['x'],r['z'])+.4,energy=.01,hydration=.01,fatigue=1.)
        h.weather['rain']=1.;h.weather['wind']=[0.,0.]
        before=(f['x'],f['z'],f['heading']);amount=r['amount']
        for _ in range(80):h.actuate(f,np.zeros(8),DT)
        self.assertEqual(before,(f['x'],f['z'],f['heading']))
        self.assertEqual(amount,r['amount']);self.assertEqual(f['signal'],[0.,0.])
        self.assertIsNone(f['target']);self.assertEqual(f['memory'],{})
    def test_neural_motor_interventions(self):
        for channel in (0,1,2,5,6):
            h=self.world(1);f=h.flies[0];before=copy.deepcopy(f);u=np.zeros(8);u[channel]=1
            h.actuate(f,u,DT)
            if channel in (0,1):self.assertNotEqual(f['heading'],before['heading']);self.assertGreater(f['travel'],0)
            if channel==2:self.assertGreater(f['y'],before['y'])
            if channel in (5,6):self.assertEqual(f['signal'][channel-5],1)
        a,b=self.world(1),self.world(1)
        a.flies[0]['heading']=b.flies[0]['heading']=0.
        a.actuate(a.flies[0],[1,0,0,0,0,0,0,0],DT);b.actuate(b.flies[0],[0,1,0,0,0,0,0,0],DT)
        self.assertLess(a.flies[0]['heading'],b.flies[0]['heading'])
    def test_contact_requires_neural_mouth_and_pump(self):
        for mouth,pump,expected in ((0,0,False),(1,0,False),(0,1,False),(1,1,True)):
            h=self.world(1);f=h.flies[0];r=h.resources[0]
            f.update(x=r['x'],z=r['z'],y=height(r['x'],r['z'])+.4);before=r['amount']
            h.actuate(f,[0,0,0,mouth,pump,0,0,0],DT)
            self.assertEqual(r['amount']<before,expected)
    def test_no_behavioral_or_semantic_entry_points(self):
        h=self.world()
        for name,args in [('decide',(h.flies[0],np.ones(8))),('send',(h.flies[0],)),('broadcast',({},)),('resolve',(h.flies[0],True))]:
            with self.assertRaises(RuntimeError):getattr(h,name)(*args)
        with self.assertRaises(ValueError):h.human_message('找水')
        for action in ('plasticity','neural_enabled'):
            with self.assertRaises(ValueError):h.control(action,True)
    def test_signal_is_delayed_local_scalar_without_semantics(self):
        h=self.world();a,b=h.flies;b.update(x=a['x']+.5,z=a['z'],y=a['y'])
        a['signal']=[1.,.4];near=h.observation(b)[15:19].copy()
        self.assertTrue((near>0).all());b['x']+=20;far=h.observation(b)[15:19]
        self.assertTrue((far<near).all());h.control('communication',False)
        self.assertTrue((h.observation(b)[15:19]==0).all())
        self.assertIsNone(b['hint']);self.assertIsNone(b['directive'])
    def test_sensing_contains_no_identity_memory(self):
        h=self.world(1);f=h.flies[0];first=h.observation(f)
        for r in h.resources:r['id']='different';r['label']='无含义'
        np.testing.assert_array_equal(first,h.observation(f));self.assertEqual(f['memory'],{})
    def test_closed_loop_and_exact_resume(self):
        a=self.world()
        for _ in range(20):a.step()
        b=Habitat.restore(json.loads(json.dumps(a.dump())))
        for _ in range(20):a.step();b.step()
        self.assertEqual(a.dump(),b.dump())
        self.assertTrue(np.any(a.brains.h));self.assertTrue(all(f['target'] is None and not f['memory'] for f in a.flies))
        self.assertTrue((a.brains.theta==0).all())
        bad=a.dump();bad['schema']='habitat3d/1'
        with self.assertRaises(ValueError):Habitat.restore(bad)
    def test_environment_cannot_actuate_when_neural_output_clamped(self):
        h=self.world();h.brains.forward=lambda *a:np.zeros((2,8),np.float32)
        positions=[(f['x'],f['z'],f['heading']) for f in h.flies]
        h.control('rain');h.control('fruit');h.control('dry')
        for _ in range(100):h.step()
        self.assertEqual(positions,[(f['x'],f['z'],f['heading']) for f in h.flies])
        self.assertTrue(all(not f['memory'] and not any(f['motors']) for f in h.flies))
    def test_stepping_does_not_draw_behavioral_randomness(self):
        h=self.world()
        before=[copy.deepcopy(r.bit_generator.state) for r in h.move_rng+h.social_rng]
        for _ in range(100):h.step()
        self.assertEqual(before,[r.bit_generator.state for r in h.move_rng+h.social_rng])

    def test_solid_boundary_does_not_steer(self):
        h=self.world(1);f=h.flies[0];f.update(x=27.49,z=0.,heading=math.pi/2)
        heading=f['heading']
        for _ in range(50):h.actuate(f,[1,1,0,0,0,0,0,0],DT)
        self.assertEqual(f['heading'],heading);self.assertLessEqual(math.hypot(f['x']/27.5,f['z']/17.5),1.000001)
        self.assertEqual(f['touch'],1.)

    def test_real_circuit_brain(self):
        from real_brain import RealCircuitBrains
        brain = RealCircuitBrains(2, 7)
        self.assertEqual(brain.mode, 'real')
        self.assertEqual(brain.n, 98)
        outputs = brain.forward(np.zeros((2, 24), np.float32), 0.25)
        self.assertEqual(outputs.shape, (2, 8))
        self.assertTrue(np.isfinite(outputs).all())
        # Semantic observations must not reach the circuit: identical protocol state
        # produces identical outputs regardless of the observation vector.
        state = brain.dump()
        a = brain.forward(np.ones((2, 24), np.float32), 0.25).copy()
        brain.restore(state)
        b = brain.forward(np.zeros((2, 24), np.float32), 0.25).copy()
        np.testing.assert_array_equal(a, b)
        # Passive protocol must depolarize motor neurons above rest on some phase.
        voltages = brain.network.v[0]
        self.assertGreater(float(voltages.max()), -60.)
        # No global reward learning modifies the circuit.
        before = brain.dump()
        brain.learn(np.ones(2), True)
        self.assertEqual(brain.dump(), before)

if __name__=='__main__':unittest.main(verbosity=2)
