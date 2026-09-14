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


class ExpansionTests(unittest.TestCase):
    def test_adex_fi_curve_and_checkpoint(self):
        from physiology.spiking import SpikingNetwork, AdExParameters
        net = SpikingNetwork(2, AdExParameters(refractory_ms=2.), dt_ms=.1)
        rates = []
        for current in [0., 20., 60., 120.]:
            fresh = SpikingNetwork(2, AdExParameters(refractory_ms=2.), dt_ms=.1)
            for _ in range(2000):
                fresh.step([[current, 0.]])
            rates.append(fresh.total_spikes[0, 0])
        self.assertEqual(rates[0], 0)
        self.assertEqual(rates, sorted(rates))
        net.step([[100., 0.]])
        saved = net.snapshot()
        first = net.step([[100., 0.]])
        net.restore(saved)
        np.testing.assert_array_equal(net.step([[100., 0.]]), first)
        with self.assertRaises(ValueError):
            net.step([[0.]])
        with self.assertRaises(ValueError):
            net.restore({'fingerprint': 'x', 'ticks': 0, 'v': net.v, 'w': net.w,
                         'since_spike': net.since_spike, 'total_spikes': net.total_spikes})

    def test_cable_matches_sealed_end_analytic(self):
        from physiology.cable import CableTree, sealed_end_attenuation
        n = 200
        leak, axial = 1., 1.
        tree = CableTree(np.arange(-1, n-1), 10., leak, -60., axial, dt_ms=1.)
        drive = np.zeros(n); drive[0] = 100.
        for _ in range(2000):
            tree.step(drive)
        relative = (tree.v-tree.v[-1])/(tree.v[0]-tree.v[-1])
        length = 1./np.arccosh(1.+leak/(2.*axial))
        expected = sealed_end_attenuation(n, length)
        self.assertLess(np.max(abs(relative-expected)), .02)
        with self.assertRaises(ValueError):
            CableTree(np.array([0]), 10., 1., -60., 0.)
        saved = tree.snapshot()
        tree.step(np.zeros(n))
        tree.restore(saved)
        np.testing.assert_array_equal(tree.v, np.array(saved['v']))

    def test_gap_junction_current_balance(self):
        from physiology.gap_junctions import GapJunctions
        gj = GapJunctions(3, [0, 1], [1, 2], [2., 3.], 'fixture evidence')
        current = gj.current_pa(np.array([-60., -50., -40.]))
        self.assertAlmostEqual(float(current.sum()), 0., places=9)
        # Middle node both loses to 0 (2 nS * 10 mV) and gains from 2 (3 nS * 10 mV).
        np.testing.assert_allclose(current, [20., 10., -30.])
        with self.assertRaises(ValueError):
            GapJunctions(3, [0], [0], [1.], 'self coupling')

    def test_modulator_pool_and_bounded_gain(self):
        from physiology.neuromodulation import ModulatorPool, ReceptorMap
        pool = ModulatorPool('dopamine', 10., baseline_nm=1.)
        pool.release(9.)
        self.assertEqual(pool.concentration_nm, 10.)
        pool.step(10.)
        self.assertAlmostEqual(pool.concentration_nm, 1.+9.*np.exp(-1.), places=9)
        receptors = ReceptorMap([{'modulator': 'dopamine', 'receptor': 'DopR1',
            'targets': [0], 'lower': .5, 'upper': 2., 'evidence': 'fixture'}])
        low, touched = receptors.gain('dopamine', 0., 1., 3)
        np.testing.assert_array_equal(low, np.ones(3))
        self.assertFalse(touched.any())
        high, touched = receptors.gain('dopamine', 1e6, 1., 3)
        self.assertLess(high[0], 2.+1e-9)
        self.assertTrue(touched[0] and not touched[1])
        with self.assertRaises(ValueError):
            ReceptorMap([{'modulator': 'dopamine', 'receptor': 'DopR1',
                'targets': [0], 'lower': 2., 'upper': 1., 'evidence': 'x'}])

    def test_mb_plasticity_gated_and_bounded(self):
        from physiology.mb_learning import CompartmentPlasticity
        rule = CompartmentPlasticity(4, [0, 0, 1, 1], [.001, .01], [(.5, 2.), (.8, 1.2)],
                                     'compartment heterogeneity fixture', 50.)
        w = np.ones(4); pre = np.ones(4); post = np.ones(4)
        slow = rule.step(w, pre, post, 0., 10.)
        np.testing.assert_array_equal(slow, w)
        for _ in range(3):
            mild = rule.step(w, pre, post, 1., 10.)
        self.assertGreater(mild[3]-1., mild[1]-1.)  # rate heterogeneity, no clipping
        hot = rule.step(w, pre, post, 1000., 10.)
        self.assertLessEqual(hot.max(), 2.)         # bounds respected
        with self.assertRaises(ValueError):
            rule.step(w, pre, post, -1., 10.)

    def test_circadian_period_and_gate_bounds(self):
        from physiology.circadian import CircadianClock, ArousalGate
        clock = CircadianClock(24., .5)
        peaks = []
        for _ in range(int(24/.5*3)):
            peaks.append(clock.step())
        self.assertAlmostEqual(max(peaks), 1.)
        self.assertGreater(len([p for p in peaks if p > .9]), 1)
        gate = ArousalGate(.5, 2., (.2, 1.5))
        awake = gate.step(1., 1.)
        for _ in range(50):
            asleep = gate.step(0., 1.)
        self.assertGreater(awake, 1.4)
        self.assertLess(asleep, .3)
        with self.assertRaises(ValueError):
            CircadianClock(-1., 1.)

    def test_recruitment_order_and_force(self):
        from body.recruitment import MotorUnit, MotorUnitPool
        slow = MotorUnit(1, 'tibia_flexor', 5., .013, 100., 'Azevedo 2020 slow slope')
        fast = MotorUnit(2, 'tibia_flexor', 40., 10., 20., 'Azevedo 2020 fast')
        pool = MotorUnitPool([fast, slow])
        self.assertEqual(pool.order(), [1, 2])  # slow first by threshold, not by id
        self.assertEqual(pool.recruited(4.), {1: False, 2: False})
        self.assertEqual(pool.recruited(5.), {1: True, 2: False})
        force = pool.step(np.array([50., 0.]), 1.)
        self.assertGreater(force['tibia_flexor'], 0.)
        zero = pool.step(np.array([0., 0.]), 1.)
        with self.assertRaises(ValueError):
            pool.step(np.array([0.]), 1.)

    def test_male_calibration_requires_male_measurement(self):
        from body.male_calibration import MassMeasurement, calibration_factor
        male = MassMeasurement('male', 'Canton-S', 2., 0.81,
                               'Zumstein et al. 2004 JEB 207:3515-3522')
        with self.assertRaises(ValueError):
            MassMeasurement('female', 'Canton-S', 2., 1.13, 'same')
        class Stub:
            body_mass = np.full(73, 0.014)
        factor, receipt = calibration_factor(Stub(), male, 'mg')
        self.assertAlmostEqual(factor, 0.81/(0.014*73), places=9)
        self.assertFalse(receipt['biological_acceptance'])
        self.assertIn('source', receipt['measurement'])

    def test_roi_audit_requires_roi_column(self):
        from connectome.roi_audit import audit
        neurons = pd.DataFrame({'body_id': [1, 2]})
        with self.assertRaises(ValueError):
            audit(pd.DataFrame({'pre_body_id': [1], 'post_body_id': [2]}), neurons)
        synapses = pd.DataFrame({'pre_body_id': [1, 1, 9], 'post_body_id': [2, 9, 2],
                                 'roi': ['ME(R)', 'GNG', 'ME(R)']})
        result = audit(synapses, neurons)
        self.assertEqual(result['conservation']['internal_rows'], 1)
        self.assertEqual(result['conservation']['incoming_boundary_rows'], 1)
        self.assertEqual(result['conservation']['outgoing_boundary_rows'], 1)
        self.assertEqual(result['roi_partition'].set_index('roi').loc['ME(R)', 'internal_rows'], 1)

    def test_stimulus_protocol_is_frozen_data(self):
        from experiments.stimulus_protocols import CurrentProtocol
        a = CurrentProtocol([0, 1], .1, 'step', 10., 30., seed=3)
        b = CurrentProtocol([0, 1], .1, 'step', 10., 30., seed=3)
        c = CurrentProtocol([0, 1], .1, 'step', 10., 31., seed=3)
        self.assertEqual(a.fingerprint, b.fingerprint)
        self.assertNotEqual(a.fingerprint, c.fingerprint)
        np.testing.assert_array_equal(a.current_pa(4, 5)[[0, 1]], [30., 30.])
        with self.assertRaises(ValueError):
            a.current_pa(4, 100)

    def test_light_and_nutrient_fields(self):
        from world.light import photon_rate_per_m2, day_night_irradiance
        from world.nutrients import SubstratePatch
        rate = photon_rate_per_m2(np.array([1., 2.]), np.array([5.6e-7, 3.4e-7]))
        self.assertGreater(rate[1], rate[0])
        self.assertEqual(day_night_irradiance(-5.), 0.)
        self.assertGreater(day_night_irradiance(30.), 0.)
        patch = SubstratePatch(100., .8, 50.)
        denied = patch.ingest(False, 10.)
        self.assertEqual(denied['ingested_ug'], 0.)
        eaten = patch.ingest(True, 80.)
        self.assertEqual(eaten['ingested_ug'], 50.)
        self.assertEqual(patch.mass_ug, 0.)

    def test_contact_and_feeding_schedule(self):
        from world.contact import touch_events, thermal_environment, laminar_wind
        from experiments.feeding import ContactSchedule
        events = touch_events(np.array([[0., 0., -1.], [0., 0., 2.]]), 0., .5)
        np.testing.assert_array_equal(events, [True, False])
        self.assertEqual(thermal_environment(25., 23., .5)['relative_humidity'], .5)
        wind = laminar_wind([0., 0., 1.], .5)
        self.assertAlmostEqual(float(np.linalg.norm(wind)), .5, places=9)
        with self.assertRaises(ValueError):
            ContactSchedule((0., 5.), (10., 1.), 'overlapping fixture')

    def test_flight_scaffold_scaling(self):
        from body.flight import stroke_averaged_force_n, mean_wing_chord_m
        chord = mean_wing_chord_m(2.5e-3, 2.)
        base = stroke_averaged_force_n(2.5e-3, chord, 1., 200., 1.5, 1.)
        double = stroke_averaged_force_n(2.5e-3, chord, 2., 200., 1.5, 1.)
        self.assertAlmostEqual(double['lift_n'], 4.*base['lift_n'], places=12)
        with self.assertRaises(ValueError):
            stroke_averaged_force_n(-1., chord, 1., 200., 1.5, 1.)

    def test_interface_review_adjudication(self):
        from interfaces.review import adjudicate
        crosswalk = pd.read_parquet('data/graph_neurons/interfaces/manc_lf_tibia_crosswalk.parquet')
        reviewed, unresolved = adjudicate(crosswalk)
        self.assertEqual(len(reviewed), 6)
        self.assertEqual(len(unresolved), 1)
        self.assertEqual(unresolved[0]['body_id'], 819384)
        self.assertIn('Acc. ti flexor', unresolved[0]['manc_type'])
        self.assertTrue(reviewed.delay_ms.ge(0).all())
        self.assertTrue(reviewed.confidence.between(0, 1).all())
        self.assertIn('automated', reviewed.reviewer.iloc[0])
        self.assertIn('LFTibia_flex_93434', set(reviewed.target_muscle))
        self.assertIn('LFTibia_extensor_93932', set(reviewed.target_muscle))

    def test_literature_priors_carry_evidence_classes(self):
        from physiology.literature_priors import records
        table = records()
        self.assertGreater(len(table), 15)
        for row in table:
            self.assertTrue(row['source'])
            self.assertIn(row['measured_or_inferred'], ['measured', 'inferred', 'software_fixture'])
        measured = [r for r in table if r['measured_or_inferred'] == 'measured']
        self.assertGreaterEqual(len(measured), 5)
        self.assertTrue(all('female' in r['applicable_sex_age_temperature'] for r in measured))

    def test_receptor_hypotheses_dual_glutamate_and_no_unclear(self):
        from connectome.receptor_hypotheses import HYPOTHESES
        glutamate = [h for h in HYPOTHESES if h['transmitter'] == 'glutamate']
        self.assertEqual(len(glutamate), 2)
        self.assertAlmostEqual(sum(h['probability'] for h in glutamate), 1.)
        signs = {h['polarity'] for h in glutamate}
        self.assertEqual(signs, {'excitatory', 'inhibitory'})
        self.assertNotIn('unclear', {h['transmitter'] for h in HYPOTHESES})
        for h in HYPOTHESES:
            self.assertTrue(h['evidence'])
            if h['polarity'] in ('excitatory', 'inhibitory'):
                self.assertIsInstance(h['reversal_potential_mv'], float)
            else:
                self.assertIsNone(h['reversal_potential_mv'])

    def test_synapse_coverage_stream_counts(self):
        import tempfile
        import pyarrow as pa
        from connectome.synapse_coverage import stream
        batch = pa.record_batch({
            'body': pa.array([1, 1, 9, 2, 2, 9], type=pa.uint64()),
            'kind': pa.array(['PreSyn', 'PostSyn', 'PreSyn', 'PostSyn', 'PostSyn', 'PostSyn']),
            'roi': pa.array([['ME(R)', 'GNG'], ['ME(R)'], ['GNG'], ['LegNp(T1)(L)'], None, ['GNG']]),
        })
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'points.feather'
            with pa.OSFile(str(path), 'wb') as sink:
                writer = pa.ipc.RecordBatchFileWriter(sink, batch.schema)
                writer.write_batch(batch)
                writer.close()
            result = stream(Path(path), np.array([1, 2], dtype=np.uint64))
        self.assertEqual(result['totals'], {'known_pre': 1, 'known_post': 3,
                                            'unknown_pre': 1, 'unknown_post': 1})
        self.assertEqual(result['roi_known']['ME(R)'], [1, 1])
        self.assertEqual(result['roi_known']['GNG'], [1, 0])  # row 0 is known PreSyn listing GNG
        self.assertEqual(result['roi_known']['LegNp(T1)(L)'], [0, 1])
        self.assertEqual(result['roi_unknown']['GNG'], [1, 1])
        self.assertEqual(result['roi_known'].get('unassigned'), [0, 1])
        np.testing.assert_array_equal(result['body_counts'], [[1, 1], [0, 2]])

    def test_unit_conversions_and_perturbations(self):
        from interfaces.unit_conversions import deg_to_rad, rad_to_deg, voltage_to_current_pa, spike_rate_hz
        self.assertAlmostEqual(float(deg_to_rad(180.)), np.pi, places=12)
        self.assertAlmostEqual(float(rad_to_deg(np.pi/2)), 90., places=12)
        np.testing.assert_allclose(voltage_to_current_pa(np.array([-60., 0.]), 2.), [-120., 0.])
        self.assertEqual(spike_rate_hz(30, 1.), 30.)
        from experiments.perturbations import Perturbation
        activation = Perturbation('activate', [0, 2], 'fixture', 100., amplitude_pa=50.)
        np.testing.assert_array_equal(activation.current_pa(3), [50., 0., 50.])
        self.assertTrue(Perturbation('silence', [1], 'fixture', 50., clamp_mv=-70.).targets_silent())
        with self.assertRaises(ValueError):
            Perturbation('silence', [1], 'fixture', 50.)
        with self.assertRaises(ValueError):
            Perturbation('delete', [1], 'fixture', 50.)

    def test_motor_trial_metrics_and_identity(self):
        from experiments.motor_trials import trial_metrics, DRIVER_CLASS, driver_identity
        voltage = np.r_[np.full(1200, -45.), np.full(2000, -45.+11.7), np.full(1000, -45.)]
        metrics = trial_metrics(voltage, np.zeros(4200), 62.5)
        self.assertFalse(metrics['spiked'])
        self.assertAlmostEqual(metrics['delta_mv'], 11.7, places=9)
        spiking = voltage.copy(); spiking[1300] = 10.
        self.assertTrue(trial_metrics(spiking, np.zeros(4200), 62.5)['spiked'])
        self.assertIn('22a08', DRIVER_CLASS)
        self.assertIn('intermediate', DRIVER_CLASS['22a08'])
        import zipfile
        archive = zipfile.ZipFile('data/physiology_raw/motor/180222_F1_C1.zip')
        tag, identity, notes = driver_identity(archive)
        self.assertEqual(tag, '22a08')
        self.assertIn('intermediate', identity)
        self.assertTrue(notes.startswith('notes_'))

    def test_feco_identity_mapping_content(self):
        table = pd.read_parquet('data/graph_neurons/interfaces/feco_identity.parquet')
        self.assertEqual(len(table[table.role == 'hook afferent (SNpp38)']), 6)
        chief = table[table.role == 'chief 9A T1L']
        self.assertEqual(int(chief.malecns_body_id.iloc[0]), 805450)
        self.assertEqual(chief.mapping_status.iloc[0], 'mapped_type_consistent')
        flagged = table[table.mapping_status == 'mapped_type_inconsistent_manual_review']
        self.assertEqual(len(flagged), 1)  # MANC 13157 double map, SNpp41 row

    def test_feco_preregister_models(self):
        from experiments.feco_preregister import _predictions, THRESHOLD
        t = np.linspace(0, 1, 200)
        flexion = 90.+40.*np.sin(2*np.pi*t)
        hook = _predictions('hook_flexion_01_magnet_Mamiya2018.parquet', flexion, 200.)
        extension = _predictions('hook_extension_magnet.parquet', flexion, 200.)
        claw = _predictions('claw_magnet_Mamiya2018.parquet', flexion, 200.)
        club = _predictions('club_magnet_Mamiya2018.parquet', flexion, 200.)
        self.assertGreater(hook.max(), 0.)      # flexion-selective phasic responds
        self.assertGreater(extension.max(), 0.) # mirrored selectivity also responds here
        np.testing.assert_allclose(claw, flexion)  # tonic position is identity
        self.assertGreater(club.max(), 0.)      # rectified speed responds
        self.assertEqual(THRESHOLD['majority_of_test_trials'], .5)

    def test_proprioceptive_channels(self):
        from body.proprioception import ProprioceptiveChannel, femoral_chordotonal_hypothesis
        channel = ProprioceptiveChannel('joint_LFTibia_pitch', 'position_rad', 100., 1.0, 'fixture evidence')
        self.assertAlmostEqual(channel.current_pa(1.5), 50., places=9)
        velocity = ProprioceptiveChannel('joint_LFTibia_pitch', 'velocity_rad_s', 10., .5, 'fixture evidence')
        self.assertAlmostEqual(velocity.current_pa(-1.), -15., places=9)  # signed linear encoding
        response = femoral_chordotonal_hypothesis(np.array([1., 2.]), np.array([-4., 0.]), 10., 5., 1., 1., 'fixture')
        np.testing.assert_allclose(response['static_pa'], [0., 10.])
        np.testing.assert_allclose(response['dynamic_pa'], [-15., 0.])  # dead zone below threshold
        with self.assertRaises(ValueError):
            ProprioceptiveChannel('joint', 'torque', 1., 0., 'fixture')

    def test_background_noise_is_reproducible_and_colored(self):
        from physiology.background import BackgroundCurrent
        a, b = BackgroundCurrent(4, 50., 10., seed=7), BackgroundCurrent(4, 50., 10., seed=7)
        other = BackgroundCurrent(4, 50., 10., seed=8)
        samples_a = [a.step(.1) for _ in range(10000)]
        samples_b = [b.step(.1) for _ in range(10000)]
        samples_other = [other.step(.1) for _ in range(10000)]
        np.testing.assert_array_equal(np.asarray(samples_a), np.asarray(samples_b))
        self.assertFalse(np.array_equal(np.asarray(samples_a), np.asarray(samples_other)))
        sigma_empirical = float(np.std(np.asarray(samples_a)[1000:], axis=0).mean())
        # Stationary OU standard deviation is sigma (parameter is the stationary scale);
        # correlation time ~500 steps leaves ~80 effective samples, so allow 20%.
        self.assertLess(abs(sigma_empirical-10.)/10., .2)
        saved = a.snapshot()
        first = a.step(.1)
        a.restore(saved)
        np.testing.assert_array_equal(a.step(.1), first)

    def test_roi_crosscheck_detects_disagreement(self):
        import tempfile
        from connectome.roi_crosscheck import crosscheck
        coverage = pd.DataFrame({'roi': ['A', 'A', 'B'], 'known_pre': [80., 10., 0.],
                                 'known_post': [0., 0., 50.], 'unknown_pre': [20., 0., 0.],
                                 'unknown_post': [100., 0., 50.]})
        paper = pd.DataFrame({'roi': ['A', 'B'], 'PreSyn': [110, 0], 'PostSyn': [100, 100],
                              'presyn_traced_frac': [.8, np.nan],
                              'postsyn_traced_frac': [.0, .2]})
        with tempfile.TemporaryDirectory() as tmp:
            cov_path, paper_path = Path(tmp)/'cov.parquet', Path(tmp)/'paper.csv'
            coverage.to_parquet(cov_path, index=False)
            paper.to_csv(paper_path, index=False)
            merged, summary = crosscheck(cov_path, paper_path, minimum_sides=0)
        self.assertEqual(summary['matched_rois'], 2)
        self.assertAlmostEqual(summary['max_pre_count_relerr'], 0., places=12)
        self.assertAlmostEqual(summary['max_postsyn_frac_diff'], .3, places=9)  # B flags disagreement


if __name__ == '__main__':
    unittest.main()
