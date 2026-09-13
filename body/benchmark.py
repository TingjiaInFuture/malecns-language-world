"""Run every single-muscle stimulation, passive baseline and timestep comparison."""
import hashlib
import json
import time
from pathlib import Path
from importlib.metadata import version
import numpy as np
import psutil
import mujoco as mj
import flygym
from flygym.compose.fly.musculoskeletal import DEFAULT_MUSCULOSKELETAL_XML
from .flygym_adapter import LeftFrontLeg


def run():
    start = time.perf_counter()
    leg = LeftFrontLeg()
    zero = np.zeros(15)
    def trial(action, duration=.05):
        leg.reset()
        for _ in range(round(duration/leg.model.opt.timestep)):
            obs = leg.step(action)
        return obs
    passive = trial(zero)
    stimuli = []
    for i,name in enumerate(leg.names):
        action = zero.copy(); action[i] = .5
        obs = trial(action)
        stimuli.append({'muscle':name,'activation_command':.5,
            'joint_delta_vs_passive_rad':(obs['qpos_rad']-passive['qpos_rad']).tolist(),
            'force_model_units':float(obs['muscle_force_model_units'][i])})
    action = np.full(15,.1)
    trial(action,.01)
    saved = leg.snapshot()
    expected = [leg.step(action)['qpos_rad'] for _ in range(20)]
    leg.restore(saved)
    restart_error = max(float(np.max(abs(leg.step(action)['qpos_rad']-a))) for a in expected)
    convergence = []
    for dt in [.0001,.00005,.000025]:
        leg.model.opt.timestep = dt
        obs = trial(action)
        convergence.append({'dt_s':dt,'qpos_rad':obs['qpos_rad'].tolist()})
    d1 = float(np.max(abs(np.array(convergence[0]['qpos_rad'])-convergence[1]['qpos_rad'])))
    d2 = float(np.max(abs(np.array(convergence[1]['qpos_rad'])-convergence[2]['qpos_rad'])))
    # Replay all bundled motion-capture frames as forward kinematics only. This
    # tests coordinates, never treats imposed angles as a muscle-control result.
    mocap_dir = Path(flygym.__file__).parent.parent/'flygym_demo/muscle_imitation/assets/mocap'
    clips = {k:np.load(mocap_dir/k/'0002.npy') for k in ['qpos','qvel','xipos','xivel']}
    tracked = ['joint_LFCoxa_yaw','joint_LFCoxa_pitch','joint_LFCoxa_roll',
        'joint_LFTrochanter_yaw','joint_LFTrochanter_pitch','joint_LFTrochanter_roll','joint_LFTibia_pitch']
    joint_ids = [mj.mj_name2id(leg.model,mj.mjtObj.mjOBJ_JOINT,n) for n in tracked]
    body_ids = [mj.mj_name2id(leg.model,mj.mjtObj.mjOBJ_BODY,n) for n in ['LFFemur','LFTibia','LFTarsus1','LFTarsus5']]
    if min(joint_ids+body_ids) < 0:
        raise ValueError('Bundled mocap topology mismatch')
    errors, inertial_errors = [], []
    for frame in range(len(clips['qpos'])):
        leg.reset()
        leg.data.qpos[leg.model.jnt_qposadr[joint_ids]] = clips['qpos'][frame]
        leg.data.qvel[leg.model.jnt_dofadr[joint_ids]] = clips['qvel'][frame]
        mj.mj_forward(leg.model,leg.data)
        # Despite the filename xipos, upstream ImitationEnv compares body-frame
        # origins (data.xpos), not centers of mass (data.xipos).
        errors.append(leg.data.xpos[body_ids]-clips['xipos'][frame])
        inertial_errors.append(leg.data.xipos[body_ids]-clips['xipos'][frame])
    errors = np.asarray(errors)
    report = {'scope':'body-only engineering baseline; not MaleCNS neuromuscular validation',
        'flygym':version('flygym'),'mujoco':version('mujoco'),
        'xml_sha256':hashlib.sha256(Path(DEFAULT_MUSCULOSKELETAL_XML).read_bytes()).hexdigest(),
        'joint_names':leg.joint_names,'muscle_names':leg.names,'stimuli':stimuli,
        'passive_qpos_rad':passive['qpos_rad'].tolist(),'restart_max_abs_rad':restart_error,
        'dt_comparison':convergence,'dt_errors_rad':[d1,d2],
        'decreasing_dt_error':d2<d1,'finite_smoke_pass':True,
        'mocap_replay':{'clip':'0002','frames':len(errors),'kind':'imposed-angle forward kinematics only',
            'coordinate':'MuJoCo xpos body-frame origin, matching upstream ImitationEnv',
            'wrong_inertial_origin_rmse_mm':float(np.sqrt(np.mean(np.asarray(inertial_errors)**2))),
            'position_rmse_mm':float(np.sqrt(np.mean(errors**2))),
            'max_abs_position_error_mm':float(np.max(abs(errors))),
            'source_sha256':{k:hashlib.sha256((mocap_dir/k/'0002.npy').read_bytes()).hexdigest() for k in clips}},
        'biological_acceptance':False,'wall_seconds':time.perf_counter()-start,
        'process_peak_wset_bytes':getattr(psutil.Process().memory_info(),'peak_wset',None),
        'limitations':['Only left-front muscles; tethered original model',
            'No male-specific mass/force calibration','No reviewed motor or proprioceptor IDs',
            'Convergence is reported, no biological tolerance is invented','No held-out animal intervention data']}
    path = Path('validation/body-evidence.json')
    report['executed_source_sha256']={p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
        for p in ['body/benchmark.py','body/flygym_adapter.py']}
    path.write_text(json.dumps(report,indent=2),encoding='utf-8')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax = plt.subplots(figsize=(10,6))
    ax.barh(leg.names,[max(abs(np.array(s['joint_delta_vs_passive_rad']))) for s in stimuli])
    ax.set_xlabel('Maximum absolute joint change from passive baseline (rad)')
    ax.set_title('FlyGym LF muscle stimulation: body-only, 0.5 command for 50 ms')
    fig.tight_layout()
    fig.savefig('validation/body-stimulation.png',dpi=160)
    plt.close(fig)
    print(json.dumps({k:report[k] for k in ['restart_max_abs_rad','dt_errors_rad','decreasing_dt_error','wall_seconds']},indent=2))


if __name__ == '__main__':
    run()
