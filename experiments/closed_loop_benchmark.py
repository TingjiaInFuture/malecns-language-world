"""Real MuJoCo body with an explicitly synthetic neural circuit and causal controls.

This benchmark tests integration only. fixture:* IDs are NOT MaleCNS neurons.
"""
import json
import hashlib
from pathlib import Path
from dataclasses import replace
import time
import numpy as np
import psutil
from body.flygym_adapter import LeftFrontLeg
from physiology.reference import ConductanceNetwork
from physiology.plasticity import ModulatedEligibility
from .embodied import EmbodiedExperiment, SensoryPort, MotorPort
from .controls import degree_preserving_rewire


def make(seed=0, control='intact'):
    body = LeftFrontLeg()
    pre = np.array([0,0,1,1,2,2,3,3,4,5])
    post = np.array([2,3,2,3,4,5,4,5,1,0])
    g = np.full(len(pre),1.5)
    audit = {}
    if control == 'no_connectome':
        g.fill(0)
    if control == 'rewired':
        pre,post,audit = degree_preserving_rewire(pre,post,seed)
    brain = ConductanceNetwork(6,pre,post,g,np.zeros(len(pre)),np.full(len(pre),1.),dt_ms=.1)
    ids = ['fixture:'+str(i) for i in range(6)]
    joint = 'joint_LFTibia_pitch'
    sensory = [SensoryPort(ids[0],joint,'qpos_rad',20.,0.,1.,'software fixture; not anatomy'),
               SensoryPort(ids[1],joint,'qvel_rad_s',.2,0.,1.,'software fixture; not anatomy')]
    motor = [MotorPort(ids[4],'LFTibia_flex_93434',-60.,.04,1.,'software fixture; not anatomy'),
             MotorPort(ids[5],'LFTibia_extensor_93932',-55.,.025,1.,'software fixture; not anatomy')]
    if control == 'shuffled_io':
        sensory = [replace(p,neuron_id=ids[i]) for p,i in zip(sensory,[4,5])]
        motor = [replace(p,neuron_id=ids[i]) for p,i in zip(motor,[0,1])]
    learning=ModulatedEligibility(brain.g.shape,pre==2,'synthetic local plasticity fixture, not MB evidence',10.,.001)
    return EmbodiedExperiment(brain,body,ids,sensory,motor,learning=learning),audit


def run():
    records = []
    for control in ['intact','no_connectome','rewired','shuffled_io','no_proprioception','motor_clamp','no_modulation']:
        experiment,audit = make(37,control)
        start = time.perf_counter()
        trajectory = []
        for _ in range(10):
            state = experiment.run(10.,proprioception=control!='no_proprioception',neural_clamp=control=='motor_clamp',
                modulator=np.full_like(experiment.brain.g,0. if control=='no_modulation' else 1.))
            trajectory.append({'time_ms':state['time_ms'],'qpos_rad':state['body']['qpos_rad'].tolist(),
                'voltage_mv':state['voltage_mv'].tolist(),'muscle_commands':state['muscle_commands'].tolist()})
        wall = time.perf_counter()-start
        records.append({'control':control,'seed':37,'simulated_seconds':.1,'wall_seconds':wall,
            'wall_seconds_per_simulated_second':wall/.1,'subsystem_wall_seconds':experiment.timings,
            'events':experiment.events,'rewire':audit,'trajectory':trajectory})
        records[-1]['max_efficacy_change']=float(np.max(abs(experiment.brain.efficacy-1)))
    experiment,_ = make()
    modulation=np.ones_like(experiment.brain.g)
    experiment.run(30.,modulator=modulation)
    checkpoint = experiment.snapshot()
    expected = experiment.run(20.,modulator=modulation)
    expected_weights=experiment.brain.efficacy.copy()
    experiment.restore(checkpoint)
    actual = experiment.run(20.,modulator=modulation)
    errors = {'voltage_mv':float(np.max(abs(expected['voltage_mv']-actual['voltage_mv']))),
        'joint_rad':float(np.max(abs(expected['body']['qpos_rad']-actual['body']['qpos_rad']))),
        'efficacy':float(np.max(abs(expected_weights-experiment.brain.efficacy)))}
    frozen = experiment.snapshot()
    for _ in range(1000):
        view = experiment.observe()
        view['voltage_mv'].fill(999)
    observer_unchanged = np.array_equal(experiment.brain.v,frozen['brain']['v']) and experiment.tick==frozen['tick']
    result = {'scope':'software_fixture_with_FlyGym_body','biological_acceptance':False,
        'conditions':'No animal sex/age/strain attribution; uncalibrated fixture parameters',
        'records':records,'restart_errors':errors,'observer_read_only':observer_unchanged,
        'peak_wset_bytes':getattr(psutil.Process().memory_info(),'peak_wset',None),
        'software_pass':all(v==0 for v in errors.values()) and observer_unchanged}
    result['executed_source_sha256']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
        for p in ['experiments/embodied.py','experiments/closed_loop_benchmark.py','experiments/controls.py',
                  'physiology/reference.py','physiology/plasticity.py','body/flygym_adapter.py']}
    Path('validation/closed-loop-evidence.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['software_pass','restart_errors','observer_read_only','peak_wset_bytes']},indent=2))
    if not result['software_pass']:
        raise RuntimeError('Closed loop integration validation failed')


if __name__ == '__main__':
    run()
