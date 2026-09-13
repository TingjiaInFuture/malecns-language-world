"""Software fixtures only; these tests contain no biological observations."""
import unittest
import numpy as np
import pandas as pd
from experiments.feco import FIELDS, hook_fluorescence, split_animals, validate_frame
from interfaces.manc_crosswalk import join_candidates


class PublicDataTests(unittest.TestCase):
    def test_animal_split_order_invariant_and_disjoint(self):
        animals=list('abcdefghij')
        split=split_animals(animals)
        self.assertEqual(split,split_animals(animals[::-1]+animals))
        self.assertEqual(set(split),set(animals))
        self.assertEqual(set(split.values()),{'train','validation','test'})
        with self.assertRaises(ValueError):split_animals(['a','b'])

    def test_measured_target_only(self):
        self.assertIn('calcium',FIELDS)
        self.assertNotIn('predicted_calcium',FIELDS)
        frame=pd.DataFrame({key:[0,1] for key in FIELDS})
        frame['animal_id']='fixture';frame['trial']=0
        validate_frame(frame)
        frame['time']=[1,0]
        with self.assertRaises(ValueError):validate_frame(frame)
        with self.assertRaises(ValueError):validate_frame(frame.drop(columns='calcium'))

    def test_filter_direction_and_source_convolution(self):
        self.assertTrue(np.allclose(hook_fluorescence(np.arange(100.),100),0))
        self.assertTrue(np.allclose(hook_fluorescence(np.ones(100),100),0))
        time=np.linspace(0,1,100)
        kernel=np.exp(-time/.3)-np.exp(-time/.03)
        expected=np.convolve(np.ones(100),kernel/kernel.sum())[:100]
        np.testing.assert_allclose(hook_fluorescence(-np.arange(100.),100),expected,atol=1e-14)
        with self.assertRaises(ValueError):hook_fluorescence([1,2],100,float('nan'))

    def test_crosswalk_preserves_conflicts_missing_and_unknown_confidence(self):
        candidates=pd.DataFrame({'body_id':[1,2,3],'mancBodyid':[10,20,30],
                                 'neuron_type':['flexor','flexor','extensor']})
        matching=pd.DataFrame({'bodyid':[10,20],'type':['flexor','accessory'],
                               'match_certainty(1-5)':[np.nan,2]})
        serial=pd.DataFrame({'bodyid':[10,20],'soma_side':['LHS','LHS']})
        result=join_candidates(candidates,matching,serial)
        self.assertEqual(list(result.crosswalk_status),['candidate_type_agreement','type_conflict','missing_supplement_identity'])
        self.assertFalse(result.approved_production_io.any())
        self.assertFalse(result.confidence_available.iloc[0])
        with self.assertRaises(ValueError):join_candidates(candidates,pd.concat([matching,matching]),serial)


if __name__=='__main__':unittest.main()
