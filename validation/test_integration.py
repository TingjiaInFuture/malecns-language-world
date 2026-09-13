import unittest
import numpy as np
from experiments.controls import degree_preserving_rewire
from experiments.calibration import fit_ensemble, validate_protocol, assess


class IntegrationTests(unittest.TestCase):
    def test_heterogeneous_membrane_analytic(self):
        from physiology.reference import ConductanceNetwork,Parameters
        p=Parameters(capacitance_pf=np.array([10.,20.]),adaptation_ns=0.)
        b=ConductanceNetwork(2,[],[],[],[],[],parameters=p)
        for _ in range(100):b.step([[10.,10.]])
        np.testing.assert_allclose(b.v[0],-50-10*np.exp(-10/np.array([10.,20.])),atol=1e-11)
        self.assertFalse(p.capacitance_pf.flags.writeable)

    def test_parameter_prior_provenance_and_reproducibility(self):
        from physiology.parameter_tables import sample_parameters,UNITS
        from physiology.reference import Parameters
        rows=[{'type_or_class':'class','parameter':k,'unit':UNITS[k],'source':'analytic fixture',
            'applicable_sex_age_temperature':'not biological','measured_or_inferred':'software_fixture',
            'value_or_distribution':{'kind':'fixed','value':v}} for k,v in vars(Parameters()).items()]
        a,_=sample_parameters(['untyped'],['class'],rows,3)
        self.assertEqual(a.capacitance_pf[0],10.)
        with self.assertRaises(ValueError):sample_parameters(['untyped'],['class'],rows[:-1],3)

    def test_rewiring_degrees_and_uniqueness(self):
        p=np.array([0,0,1,1,2,2,3,3,4,5]); q=np.array([2,3,2,3,4,5,4,5,1,0])
        a,b,audit=degree_preserving_rewire(p,q,37)
        np.testing.assert_array_equal(np.bincount(a),np.bincount(p))
        np.testing.assert_array_equal(np.bincount(b),np.bincount(q))
        self.assertEqual(len(set(zip(a,b))),len(p))
        self.assertGreater(audit['changed_edges'],0)

    def test_calibration_recovers_analytic_fixture(self):
        t=np.linspace(0,20,50); y=np.exp(-t/7.)
        fits=fit_ensemble(lambda x:np.exp(-t/x[0])-y,[[3.],[15.]],[1.],[30.],[10.],[10.],prior_weight=0)
        for fit in fits:
            self.assertAlmostEqual(fit['parameters'][0],7.,places=4)

    def protocol(self):
        p={'protocol_id':'fixture','registered_at':'2026-01-01T00:00:00+00:00',
            'dataset_sha256':['a'*64],'scope':'software_fixture',
            'conditions':{'sex':'fixture','age_days':0,'strain':'fixture','temperature_c':25,
                'light_protocol':'fixture','nutrition':'fixture'},
            'thresholds':{'error':{'maximum':.1,'unit':'mV','reliability_source':'analytic fixture'}}}
        r=[{'animal_id':str(i),'trajectory_id':str(i),'split':split,'dataset_sha256':'a'*64,
            'evaluated_at':'2026-01-02T00:00:00+00:00'} for i,split in enumerate(['train','validation','test'])]
        return p,r

    def test_preregistration_and_leakage(self):
        p,r=self.protocol()
        self.assertEqual(len(validate_protocol(p,r)),64)
        r[1]['animal_id']=r[0]['animal_id']
        with self.assertRaises(ValueError):validate_protocol(p,r)

    def test_retroactive_registration_rejected(self):
        p,r=self.protocol(); p['registered_at']='2026-01-03T00:00:00+00:00'
        with self.assertRaises(ValueError):validate_protocol(p,r)

    def test_missing_metric_cannot_pass(self):
        p,_=self.protocol()
        self.assertFalse(assess(p,{},'software_fixture')['thresholds_pass'])
        self.assertFalse(assess(p,{'error':0.},'software_fixture')['biological_acceptance'])


if __name__=='__main__':unittest.main()
