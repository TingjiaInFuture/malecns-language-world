import sys
import unittest
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from connectome.compiler import identities, membership
from physiology.reference import ConductanceNetwork, Parameters


class ReferenceTests(unittest.TestCase):
    def test_no_unreviewed_ports(self):
        from interfaces.registry import validate
        with self.assertRaises(ValueError):
            validate(pd.DataFrame(),pd.DataFrame(),'motor')

    def test_clock_and_physical_stimuli(self):
        from physiology.clock import MultiClock
        from world.stimuli import taste_concentration, odor_puff_mol_m3
        c = MultiClock(.1,{'neural':.1,'body':.2,'slow':10})
        due = [c.advance() for _ in range(100)]
        self.assertEqual(sum('body' in d for d in due),50)
        self.assertEqual(sum('slow' in d for d in due),1)
        self.assertEqual(taste_concentration(False,10.),0.)
        center = odor_puff_mol_m3([0,0,0],[0,0,0],1.,1.,1.,[0,0,0])
        away = odor_puff_mol_m3([2,0,0],[0,0,0],1.,1.,1.,[0,0,0])
        self.assertGreater(center,away)

    def test_wrong_clock_checkpoint_rejected(self):
        a,b = self.passive(.1),self.passive(.2)
        with self.assertRaises(ValueError):
            b.restore(a.snapshot())

    def test_local_plasticity_mask(self):
        from physiology.plasticity import ModulatedEligibility
        rule = ModulatedEligibility((2,2),[True,False],'synthetic fixture',10.,.1)
        w = np.ones((2,2)); x = np.ones_like(w); mod = np.array([[1.,1.],[0.,0.]])
        updated = rule.step(w,x,x,mod,1.)
        self.assertGreater(updated[0,0],1.)
        np.testing.assert_array_equal(updated[:,1],w[:,1])
        np.testing.assert_array_equal(updated[1],w[1])
        np.testing.assert_array_equal(w,np.ones_like(w))

    def test_mass_balance_and_contact(self):
        from physiology.homeostasis import Homeostasis
        h = Homeostasis(10.,20.,30.)
        flow = h.step(1.,False,5.,5.,10.,2.,3.)
        self.assertAlmostEqual(h.crop_ug+h.nutrient_ug,28.)
        self.assertEqual(flow['ingested_ug'],0.)
        self.assertEqual(h.water_ug,27.)
        h.step(1.,True,5.,5.,10.,2.,3.)
        self.assertAlmostEqual(h.crop_ug+h.nutrient_ug,31.)

    def test_measurement_and_leakage(self):
        from experiments.measurement import Indicator, assert_disjoint_groups
        indicator = Indicator((1,),10.,1.,0.,7)
        self.assertAlmostEqual(indicator.observe([1.],10.)[0],1-np.exp(-1))
        with self.assertRaises(ValueError):
            assert_disjoint_groups([{'animal_id':'a','trajectory_id':'x','split':'train'},
                {'animal_id':'a','trajectory_id':'y','split':'test'}])

    def passive(self, dt=.1, individuals=1):
        return ConductanceNetwork(1, [], [], [], [], [], dt_ms=dt,
            parameters=Parameters(adaptation_ns=0), individuals=individuals)

    def test_passive_analytic(self):
        b = self.passive()
        for _ in range(100):
            b.step([[10.]])
        self.assertAlmostEqual(b.v[0,0], -50-10*np.exp(-1), places=11)

    def test_rest_and_individual_independence(self):
        b = self.passive(individuals=2)
        for _ in range(100):
            b.step([[10.],[0.]])
        self.assertEqual(b.v[1,0], -60.)
        self.assertGreater(b.v[0,0], -60.)

    def test_receptor_polarity(self):
        values = []
        for e in [-80.,0.]:
            b = ConductanceNetwork(2,[0],[1],[2.],[e],[0.])
            for _ in range(200):
                b.step([[30.,0.]])
            values.append(b.v[0,1])
        self.assertLess(values[0],-60.)
        self.assertGreater(values[1],-60.)

    def test_delay_and_restart(self):
        b = ConductanceNetwork(2,[0],[1],[2.],[0.],[2.])
        b.v[0,0] = -40
        for _ in range(20):
            b.step([[20.,0.]])
        self.assertEqual(b.v[0,1],-60.)
        state = b.snapshot()
        expected = [b.step([[20.,0.]]) for _ in range(30)]
        b.restore(state)
        for v in expected:
            np.testing.assert_array_equal(b.step([[20.,0.]]),v)

    def test_convergence(self):
        result = []
        for dt in [.1,.05,.025]:
            b = ConductanceNetwork(2,[0],[1],[2.],[0.],[1.],dt_ms=dt)
            for _ in range(round(20/dt)):
                b.step([[30.,0.]])
            result.append(b.v.copy())
        self.assertLess(np.max(abs(result[1]-result[2])),np.max(abs(result[0]-result[1])))
        self.assertLess(np.max(abs(result[0]-result[1])),.1)

    def test_missing_receptor_rejected(self):
        with self.assertRaises(ValueError):
            ConductanceNetwork(2,[0],[1],[2.],[float('nan')],[0.])

    def test_identity_rule_preserves_untyped(self):
        a = pd.DataFrame({'bodyId':[1,2,3], 'status':['Traced','Anchor','Traced'],
            'type':[None,'sensory',None], 'rootSide':[None]*3, 'entryNerve':[None]*3})
        n, review = identities(a)
        self.assertEqual(n.body_id.tolist(),[1,3])
        self.assertEqual(review.bodyId.tolist(),[2])
        np.testing.assert_array_equal(membership(np.array([1,3]),np.array([0,1,2,3,4])),[False,True,False,True,False])

    def test_historical_full_dt_without_loading_large_graph(self):
        from scipy import sparse
        sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'habitat3d'))
        from full_brain import FullBrains
        b = FullBrains.__new__(FullBrains)
        b.count=1; b.matrix=sparse.csr_matrix((1,1)); b.h=np.zeros((1,1),np.float32)
        b.display_indices=np.array([0]); b.input_map=np.ones((1,1)); b.output_map=np.ones((1,1))
        b.last_output=np.zeros((1,1)); b.steps=0; b._rms_valid=np.ones(1,bool)
        b.forward([[1]],0)
        self.assertEqual(b.steps,0)
        b.forward([[1]],.25)
        self.assertAlmostEqual(float(b.h[0,0]),.5*np.tanh(1),places=6)
        b.h.fill(0); b.forward([[1]],.125)
        self.assertLess(float(b.h[0,0]),.5*np.tanh(1))
        with self.assertRaises(ValueError):
            b.forward([[1]],-1)


if __name__ == '__main__':
    unittest.main()
