"""Real MaleCNS left-front-tibia circuit driving the FlyGym body. Anatomical hypothesis.

Two-phase entry honoring the repository's environment split:
  python -m experiments.lf_tibia_circuit prepare   (.venv: graph + priors -> npz)
  python -m experiments.lf_tibia_circuit run       (.venv-body: physics)

Nodes and edges come from the compiled graph: the production motor map, its
direct sensory partners, and the top premotor interneurons. Synapse polarity
follows each presynaptic cell's predicted transmitter through the reviewed
receptor hypotheses; glutamate and unclear transmitters are EXCLUDED from fast
conductances instead of silently signed. MN membrane parameters are sampled
from literature priors; other cells use declared fixtures. Sensory transfer is
a declared FeCO-style hypothesis, not measured afferent kinetics. This is the
first circuit run through approved production ports; it is not physiological
acceptance.
"""
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REVERSAL_BY_TRANSMITTER = {'acetylcholine': 0., 'gaba': -70., 'histamine': -70.}
EDGE_DELAY_MS = 2.
GAIN_NS_PER_SYNAPSE = .01
STATIC_GAIN_PA_PER_RAD = 200.
DYNAMIC_GAIN_PA_PER_RAD_S = 40.
REST_ANGLE_RAD = 1.5
SEED = 20260914
FIXTURE = {'capacitance_pf': 10., 'leak_ns': 1., 'resting_mv': -60.,
           'synapse_tau_ms': 5., 'adaptation_tau_ms': 100., 'adaptation_ns': .1}
NPZ = 'data/graph_neurons/interfaces/lf_tibia_circuit.npz'


def prepare(out_path=NPZ):
    """Graph-side step (.venv): production ports + induced edges + sampled priors."""
    import pandas as pd
    from physiology.parameter_tables import sample_parameters
    from physiology.literature_priors import records
    graph = Path('data/graph_neurons')
    production = pd.read_parquet(graph/'interfaces/motor_map.parquet')
    if production.empty:
        raise ValueError('No approved production motor ports; run interfaces.review --approve first')
    motors = production.motor_body_id.tolist()
    neurons = pd.read_parquet(graph/'neurons.parquet').set_index('body_id')
    edges = pd.read_parquet(graph/'edges.parquet', filters=[('post_body_id', 'in', motors)])
    inputs = edges.groupby('pre_body_id').structural_count.sum().sort_values(ascending=False)
    info = neurons.loc[inputs.index]
    is_sensory = info.superclass.astype(str).str.contains('sensory')
    sensory = info[is_sensory].assign(count=inputs[info[is_sensory].index]) \
        .sort_values('count', ascending=False)
    sensory_ports = sensory[sensory['count'] >= 5].index.tolist()
    interneurons = info[~is_sensory].head(25).index.tolist()
    node_ids = list(dict.fromkeys(motors+sensory_ports+interneurons+sensory.index.tolist()))
    induced = pd.read_parquet(graph/'edges.parquet', filters=[('pre_body_id', 'in', node_ids)])
    induced = induced[induced.post_body_id.isin(node_ids)]
    nt = pd.read_feather('data/raw/body-neurotransmitters-male-cns-v1.0.feather') \
        .set_index('body').consensus_nt
    transmitter = nt.reindex(induced.pre_body_id.to_numpy()).to_numpy()
    reversal = pd.Series(transmitter, index=induced.index).map(REVERSAL_BY_TRANSMITTER)
    annotated = induced.assign(reversal_mv=reversal)
    kept = annotated[reversal.notna()]
    excluded = annotated[reversal.isna()].assign(transmitter=transmitter[reversal.isna()])
    # Per-neuron parameters: literature priors for MNs, declared fixtures otherwise.
    types = np.array([neurons.at[b, 'neuron_type'] for b in node_ids], dtype=object)
    mn_mask = np.array([b in set(motors) for b in node_ids])
    mn_parameters, _ = sample_parameters(types[mn_mask].tolist(), types[mn_mask].tolist(),
                                         records(), seed=SEED)
    parameters = {}
    for key, default in FIXTURE.items():
        column = np.full(len(node_ids), default)
        sampled = np.asarray(getattr(mn_parameters, key), dtype=float)
        column[mn_mask] = sampled if sampled.ndim else sampled
        parameters[key] = column
    index = {body: i for i, body in enumerate(node_ids)}
    production_indexed = production.set_index('motor_body_id')
    node_transmitter = nt.reindex(node_ids).to_numpy()
    node_reversal = pd.Series(node_transmitter).map(REVERSAL_BY_TRANSMITTER).to_numpy(dtype=float)
    # Published-identity FeCO chain (Dallmann 2025 Supp Table 2 via interfaces.feco_identity).
    identity = pd.read_parquet(graph/'interfaces/feco_identity.parquet')
    identity = identity[identity.malecns_body_id.notna()]
    identity_nodes = [int(b) for b in identity.malecns_body_id if int(b) not in index]
    node_ids += identity_nodes
    for key in parameters:
        parameters[key] = np.r_[parameters[key], np.full(len(identity_nodes), FIXTURE[key])]
    index = {body: i for i, body in enumerate(node_ids)}
    induced_identity = pd.read_parquet(graph/'edges.parquet',
                                       filters=[('pre_body_id', 'in', node_ids)])
    induced_identity = induced_identity[induced_identity.post_body_id.isin(node_ids)]
    # Only edges involving the newly added identity nodes; the original induced
    # set is already in `kept` and must not be duplicated.
    involving_new = induced_identity.pre_body_id.isin(identity_nodes) | \
        induced_identity.post_body_id.isin(identity_nodes)
    annotated2 = induced_identity[involving_new].assign(reversal_mv=pd.Series(
        nt.reindex(induced_identity[involving_new].pre_body_id.to_numpy()).to_numpy(),
        index=induced_identity[involving_new].index).map(REVERSAL_BY_TRANSMITTER))
    kept2 = annotated2[annotated2.reversal_mv.notna()]
    node_transmitter = nt.reindex(node_ids).to_numpy()
    node_reversal = pd.Series(node_transmitter).map(REVERSAL_BY_TRANSMITTER).to_numpy(dtype=float)
    published_hooks = identity[(identity.role.str.startswith('hook afferent'))
                               & (identity.root_side == 'L')].malecns_body_id.astype(int).tolist()
    np.savez_compressed(out_path,
        node_ids=np.asarray(node_ids, dtype=np.uint64),
        pre=np.r_[kept.pre_body_id.map(index).to_numpy(dtype=np.int64),
                  kept2.pre_body_id.map(index).to_numpy(dtype=np.int64)],
        post=np.r_[kept.post_body_id.map(index).to_numpy(dtype=np.int64),
                   kept2.post_body_id.map(index).to_numpy(dtype=np.int64)],
        count=np.r_[kept.structural_count.to_numpy(dtype=np.uint64),
                    kept2.structural_count.to_numpy(dtype=np.uint64)],
        reversal_mv=np.r_[kept.reversal_mv.to_numpy(dtype=float),
                          kept2.reversal_mv.to_numpy(dtype=float)],
        node_reversal_mv=node_reversal,
        motor_ids=np.asarray(motors, dtype=np.uint64),
        motor_muscle_names=np.asarray(production_indexed.target_muscle.tolist()),
        motor_delays_ms=production_indexed.delay_ms.to_numpy(dtype=float),
        sensory_port_ids=np.asarray(sensory_ports, dtype=np.uint64),
        published_hook_port_ids=np.asarray(published_hooks, dtype=np.uint64),
        identity_node_ids=np.asarray([int(b) for b in identity.malecns_body_id], dtype=np.uint64),
        **{f'param_{k}': v for k, v in parameters.items()})
    Path(str(out_path)+'.manifest.json').write_text(json.dumps({
        'nodes': len(node_ids), 'motors': [int(x) for x in motors],
        'sensory_ports': [int(x) for x in sensory_ports],
        'published_hook_ports': [int(x) for x in published_hooks],
        'identity_nodes': identity.malecns_body_id.astype(int).tolist(),
        'identity_source': 'Dallmann 2025 Nature Supp Table 2 via interfaces.feco_identity',
        'muscles': production_indexed.target_muscle.tolist(),
        'edges_kept': int(len(kept)+len(kept2)), 'edges_excluded_unsigned': int(len(excluded)),
        'excluded_transmitter_counts': {str(k): int(v) for k, v in
            excluded.transmitter.value_counts(dropna=False).to_dict().items()},
        'mn_parameters': 'literature priors (Azevedo 2020 female flexor pool), seed '+str(SEED),
        'other_parameters': 'declared software fixtures', 'synapse_scale': GAIN_NS_PER_SYNAPSE,
        'edge_delay_ms': EDGE_DELAY_MS, 'static_gain_pa_per_rad': STATIC_GAIN_PA_PER_RAD,
        'dynamic_gain_pa_per_rad_s': DYNAMIC_GAIN_PA_PER_RAD_S,
        'rest_angle_rad': REST_ANGLE_RAD,
        'npz_sha256': hashlib.sha256(Path(out_path).read_bytes()).hexdigest()}, indent=2),
        encoding='utf-8')
    print(json.dumps({'nodes': len(node_ids), 'edges_kept': int(len(kept)+len(kept2)),
                      'excluded_unsigned': int(len(excluded))}, indent=2))


def _load_npz():
    data = np.load(NPZ, allow_pickle=False)
    manifest = json.loads(Path(NPZ+'.manifest.json').read_text(encoding='utf-8'))
    return data, manifest


def make_experiment(data, manifest, variant='full'):
    from physiology.reference import ConductanceNetwork, Parameters
    from body.flygym_adapter import LeftFrontLeg
    from experiments.embodied import EmbodiedExperiment, SensoryPort, MotorPort
    node_ids = [str(int(b)) for b in data['node_ids']]
    parameters = Parameters(**{k[len('param_'):]: data[k] for k in data.files if k.startswith('param_')})
    pre, post = data['pre'], data['post']
    reversal = data['reversal_mv'].astype(float)
    if variant == 'rewired':
        from experiments.controls import degree_preserving_rewire
        pre, post, _ = degree_preserving_rewire(pre, post, seed=SEED)
        # Polarity follows the NEW presynaptic cell; unsigned transmitters drop out.
        reversal = data['node_reversal_mv'].astype(float)[pre]
        keep = np.isfinite(reversal)
        pre, post, reversal = pre[keep], post[keep], reversal[keep]
    if variant == 'full':
        conductance = np.minimum(data['count'].astype(float)*GAIN_NS_PER_SYNAPSE, 20.)
    else:
        # Structural counts no longer align with rewired pairs; use the capped scale.
        conductance = np.full(len(pre), GAIN_NS_PER_SYNAPSE*50.)
    network = ConductanceNetwork(len(node_ids), pre.copy(), post.copy(), conductance,
                                 reversal.copy(), np.full(len(pre), EDGE_DELAY_MS),
                                 dt_ms=.1, parameters=parameters)
    node_position = {int(body): i for i, body in enumerate(data['node_ids'])}
    published = [int(b) for b in data.get('published_hook_port_ids', [])]
    sensory = [SensoryPort(node_ids[node_position[int(b)]], 'joint_LFTibia_pitch', 'qpos_rad',
                           STATIC_GAIN_PA_PER_RAD, REST_ANGLE_RAD, 5.,
                           'direct sensory->MN partner in the compiled graph; static gain declared fixture')
               for b in data['sensory_port_ids'] if int(b) not in published]
    sensory += [SensoryPort(node_ids[node_position[int(b)]], 'joint_LFTibia_pitch', 'qvel_rad_s',
                            DYNAMIC_GAIN_PA_PER_RAD_S, 0., 5.,
                            'same partner, velocity channel; FeCO-style split hypothesis')
                for b in data['sensory_port_ids'] if int(b) not in published]
    sensory += [SensoryPort(node_ids[node_position[int(b)]], 'joint_LFTibia_pitch', 'qpos_rad',
                            STATIC_GAIN_PA_PER_RAD, REST_ANGLE_RAD, 5.,
                            'PUBLISHED IDENTITY: hook afferent SNpp38 (Dallmann 2025 Supp Table 2, '
                            'MANC-type mapped); static gain still a declared fixture')
               for b in published]
    sensory += [SensoryPort(node_ids[node_position[int(b)]], 'joint_LFTibia_pitch', 'qvel_rad_s',
                            DYNAMIC_GAIN_PA_PER_RAD_S, 0., 5.,
                            'PUBLISHED IDENTITY hook afferent, velocity channel (phasic hypothesis '
                            'per Mamiya 2018 hook physiology)')
               for b in published]
    thresholds = {}
    for b in data['motor_ids']:
        thresholds[node_ids[node_position[int(b)]]] = \
            float(parameters.resting_mv[node_position[int(b)]])+10.
    motor = [MotorPort(node_ids[node_position[int(b)]], str(muscle),
                       thresholds[node_ids[node_position[int(b)]]], .05,
                       float(max(1., round(delay))),
                       'approved production port; voltage-threshold recruitment placeholder '
                       '(threshold = sampled resting + 10 mV; measured conduction delay '
                       'rounded to the exchange clock)')
             for b, muscle, delay in zip(data['motor_ids'], data['motor_muscle_names'], data['motor_delays_ms'])]
    if variant == 'shuffled_io':
        muscles = [p.muscle for p in motor]
        motor = [type(p)(p.neuron_id, muscles[(i+1) % len(muscles)], p.threshold_mv,
                         p.slope_per_mv, p.delay_ms, 'SHUFFLED CONTROL: muscle assignment rotated')
                 for i, p in enumerate(motor)]
    return EmbodiedExperiment(network, LeftFrontLeg(), node_ids, sensory, motor,
                              scope='anatomical_hypothesis',
                              condition={'circuit': 'real MaleCNS LF tibia subgraph',
                                         'variant': variant})


def run(duration_ms=400.):
    data, manifest = _load_npz()
    start = time.perf_counter()
    conditions = {'full': dict(proprioception=True),
                  'no_proprioception': dict(proprioception=False),
                  'motor_clamp': dict(proprioception=True, neural_clamp=True)}
    results = {}
    for variant, kwargs in conditions.items():
        experiment = make_experiment(data, manifest, variant='full')
        t0 = time.perf_counter()
        final = experiment.run(duration_ms, **kwargs)
        results[variant] = {'final_voltage_mv': final['voltage_mv'][0].round(4).tolist(),
                            'joint_qpos_rad': final['body']['qpos_rad'].round(5).tolist(),
                            'muscle_commands': final['muscle_commands'].round(4).tolist(),
                            'depolarized_neurons': int((final['voltage_mv'] > -30).sum()),
                            'wall_seconds': time.perf_counter()-t0}
    for variant in ['rewired', 'shuffled_io']:
        experiment = make_experiment(data, manifest, variant=variant)
        t0 = time.perf_counter()
        final = experiment.run(duration_ms, proprioception=True)
        results[variant] = {'final_voltage_mv': final['voltage_mv'][0].round(4).tolist(),
                            'joint_qpos_rad': final['body']['qpos_rad'].round(5).tolist(),
                            'muscle_commands': final['muscle_commands'].round(4).tolist(),
                            'depolarized_neurons': int((final['voltage_mv'] > -30).sum()),
                            'wall_seconds': time.perf_counter()-t0}
    report = {'scope': 'real MaleCNS LF tibia circuit on the FlyGym body; anatomical hypothesis, not acceptance',
              'created_at': datetime.now(timezone.utc).isoformat(), **manifest,
              'duration_ms': duration_ms, 'conditions': results,
              'note': 'The rewired variant keeps degree but not transmitter-specific polarity pairs; '
                      'controls are recorded as run, never selected by outcome.',
              'sign_off': 'motor_map.parquet approved by ZhangTingjia on top of automated_crosscheck_v1',
              'biological_acceptance': False,
              'executed_source_sha256': {'experiments/lf_tibia_circuit.py':
                  hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    Path('validation/lf-tibia-circuit.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'nodes': int(report['nodes']), 'edges_kept': int(report['edges_kept']),
                      'excluded_unsigned': int(report['edges_excluded_unsigned']),
                      'total_wall_seconds': time.perf_counter()-start,
                      'conditions': {k: {'qpos_rad': v['joint_qpos_rad'],
                                         'depolarized': v['depolarized_neurons']}
                                     for k, v in results.items()}}, indent=2))
    return report


if __name__ == '__main__':
    import sys
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if mode == 'prepare':
        prepare()
    else:
        run()
