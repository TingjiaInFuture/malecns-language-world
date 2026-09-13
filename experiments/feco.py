"""FeCO measured-fluorescence data adapter and literature observation reference.

Never read predicted_calcium as a target. No MaleCNS ID is inferred from a driver
or multi-cell imaging ROI. This is an offline sensory test, not a closed loop.
"""
import hashlib
import json
from pathlib import Path
from datetime import datetime,timezone
import numpy as np
import pandas as pd
from scipy.signal import fftconvolve
from .public_data import sha256

FIELDS=['animal_id','trial','time','calcium','L1C_flex','L1C_flex_vel','analyze']


def hook_fluorescence(angle_deg,sampling_hz,threshold_deg_s=-50.):
    """Reproduce author's hook_flex filter convention, including linspace timing.

    30/300 ms rise/decay and -50 deg/s threshold are literature model settings,
    not measured intrinsic membrane parameters. Author source is retained locally.
    """
    x=np.asarray(angle_deg,dtype=float)
    if x.ndim!=1 or len(x)<2 or not np.isfinite(x).all() or not np.isfinite(sampling_hz) or sampling_hz<=0 or not np.isfinite(threshold_deg_s):
        raise ValueError('Finite one-dimensional angle trace and sampling rate required')
    dx=np.diff(x)*sampling_hz
    dx=np.r_[dx[0],dx]
    activation=(dx<threshold_deg_s).astype(float)
    t=np.linspace(0,len(x)/sampling_hz,len(x))
    kernel=np.exp(-t/.30)-np.exp(-t/.03)
    kernel/=kernel.sum()
    return fftconvolve(activation,kernel)[:len(x)]


def split_animals(animals):
    ids=sorted(set(str(a) for a in animals),key=lambda a:hashlib.sha256(('feco-v1|'+a).encode()).hexdigest())
    if len(ids)<5:raise ValueError('At least five animals required for this registered split')
    train=max(1,int(.6*len(ids))); validation=max(1,int(.2*len(ids)))
    return {a:('train' if i<train else 'validation' if i<train+validation else 'test') for i,a in enumerate(ids)}


def validate_frame(frame):
    if set(FIELDS)-set(frame):raise ValueError('Missing measured recording fields')
    if frame[['animal_id','trial']].isna().any().any():raise ValueError('Missing animal/trial identity')
    for _,trial in frame.groupby(['animal_id','trial'],observed=True):
        t=trial.time.to_numpy()
        if len(t)<2 or not np.isfinite(t).all() or np.any(np.diff(t)<=0):raise ValueError('Nonmonotonic trial time')


def run(path):
    path=Path(path)
    if not path.exists():raise FileNotFoundError('Measured FeCO file not downloaded: '+str(path))
    receipt=json.loads(path.with_suffix(path.suffix+'.receipt.json').read_text())
    digest=sha256(path)
    if not receipt.get('publisher_sha256_verified') or digest!=receipt['sha256']:
        raise ValueError('Publisher-verified experimental data required')
    # Inspect animal identities only before freezing split and model specification.
    identities=pd.read_parquet(path,columns=['animal_id'])
    split=split_animals(identities.animal_id)
    manifest={'dataset_sha256':digest,'split':split,'created_at':datetime.now(timezone.utc).isoformat(),
        'target':'calcium','forbidden_target':'predicted_calcium','angle_unit':'degree','time_unit':'second',
        'model':'author hook_flex threshold=-50 deg/s; kernel rise=.03 s decay=.30 s; train-only affine calibration',
        'scope':'retrospective held-out-animal sensory analysis, not prospective blinded physiology',
        'acceptance_threshold':None,'conditions':'Per-animal sex/strain/age/temperature require study metadata extraction'}
    out=Path('validation/feco');out.mkdir(parents=True,exist_ok=True)
    protocol=out/'protocol.json'
    if protocol.exists():
        previous=json.loads(protocol.read_text())
        if previous['dataset_sha256']!=digest or previous['split']!=split or previous['model']!=manifest['model']:
            raise ValueError('Frozen protocol mismatch')
    else:protocol.write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    frame=pd.read_parquet(path,columns=FIELDS)
    validate_frame(frame)
    groups=[]
    for (animal,trial),part in frame.groupby(['animal_id','trial'],observed=True,sort=False):
        dt=np.diff(part.time.to_numpy()); rate=1/np.median(dt)
        if not np.allclose(dt,1/rate,atol=1e-5,rtol=.02):raise ValueError('Irregular sampling requires explicit resampling')
        angle=part.L1C_flex.to_numpy(); measured=part.calcium.to_numpy()
        if not np.isfinite(angle).all():raise ValueError('Missing kinematics requires explicit handling')
        prediction=hook_fluorescence(angle,rate)
        use=part.analyze.eq(1).to_numpy() & np.isfinite(measured)
        groups.append({'animal':str(animal),'trial':str(trial),'split':split[str(animal)],'x':prediction[use],'y':measured[use]})
    train=[g for g in groups if g['split']=='train' and len(g['x'])]
    if not train:raise ValueError('No eligible training measurements')
    if any(not any(g['split']==label and len(g['x']) for g in groups) for label in ['validation','test']):
        raise ValueError('No eligible held-out measurements')
    x=np.concatenate([g['x'] for g in train]);y=np.concatenate([g['y'] for g in train])
    gain,offset=np.linalg.lstsq(np.c_[x,np.ones_like(x)],y,rcond=None)[0]
    baseline=float(y.mean())
    rows=[]
    for g in groups:
        if not len(g['x']):continue
        error=gain*g['x']+offset-g['y']
        rows.append({'animal_id':g['animal'],'trial':g['trial'],'split':g['split'],'n':len(error),
            'mse':float(np.mean(error**2)),'constant_baseline_mse':float(np.mean((baseline-g['y'])**2))})
    report={'dataset_sha256':digest,'protocol_sha256':sha256(protocol),'gain':float(gain),'offset':float(offset),
        'trial_metrics':rows,'biological_acceptance':False,'closed_loop_validation':False,
        'note':'Measured calcium only; model takes recorded kinematics; no MaleCNS cell identity claim'}
    (out/'sensory-results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:report[k] for k in ['gain','offset','biological_acceptance']}))


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('path',nargs='?',default='data/physiology_raw/feco/hook_flexion_01_magnet.parquet')
    run(parser.parse_args().path)
