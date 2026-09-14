"""Prospective preregistered test of modality-specific FeCO encoding.

The protocol file is written and hashed BEFORE any of the four additional
magnet-restraint datasets is downloaded or read. Each dataset gets a
model hypothesis fixed from Mamiya et al. 2018 afferent physiology (hook =
flexion- or extension-selective phasic; claw = tonic position; club =
bidirectional phasic). Thresholds are the minimal predictive-content criteria,
chosen a priori: the model must beat a per-animal constant baseline on the
majority of held-out-animal test trials AND on pooled test MSE. Evaluation
runs only after the frozen protocol exists; schema mismatches are reported,
never adapted around.
Run: python -m experiments.feco_preregister register|evaluate
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

PROTOCOL_PATH = Path('validation/feco/prospective-protocol.json')
FILES = {
    'hook_flexion_01_magnet_Mamiya2018.parquet': {
        'model': 'hook-flexion phasic filter: flexion threshold -50 deg/s, kernel rise .03 s decay .30 s',
        'kicker': 'Mamiya 2018 Neuron 100:636, Fig 4C/5C: hook afferents are flexion-selective phasic'},
    'hook_extension_magnet.parquet': {
        'model': 'hook-extension phasic filter: extension threshold +50 deg/s, same kernel, mirrored',
        'kicker': 'same afferent class driven in the extension direction'},
    'claw_magnet_Mamiya2018.parquet': {
        'model': 'claw tonic position: linear regression on femur-tibia angle',
        'kicker': 'Mamiya 2018, Fig 4A/5D-E: claw afferents are tonic position encoders'},
    'club_magnet_Mamiya2018.parquet': {
        'model': 'club bidirectional phasic: rectified angular speed |dtheta/dt| through the kernel',
        'kicker': 'Mamiya 2018, Fig 4B: club afferents respond to movement in both directions'},
}
THRESHOLD = {'majority_of_test_trials': .5,
             'pooled_test_mse_below_baseline': True,
             'justification': 'Minimal a priori criterion for predictive content on unseen animals; '
                              'not derived from any observed result.'}


def catalog_hashes():
    catalog = json.loads(Path('data/physiology_raw/feco-catalog.json').read_text(encoding='utf-8'))
    return {f['path']: f['digest'] for f in catalog['files'] if f['path'] in FILES}


def register():
    if PROTOCOL_PATH.exists():
        raise SystemExit('Protocol already frozen: '+str(PROTOCOL_PATH))
    protocol = {'created_at': datetime.now(timezone.utc).isoformat(),
        'scope': 'prospective held-out-animal test of modality-specific FeCO encoding models',
        'split_rule': 'per-animal hash split 60/20/20, identities read before targets (experiments.feco.split_animals)',
        'calibration': 'train-set-only affine fit (gain, offset) per dataset',
        'datasets': {name: {**spec, 'publisher_sha256': digest}
                     for name, spec in FILES.items()
                     for digest in [catalog_hashes().get(name)]},
        'thresholds': THRESHOLD,
        'evaluation_rule': 'For each dataset: model beats the per-animal constant calcium baseline '
                           'on >50% of test trials AND pooled test MSE < pooled baseline MSE. '
                           'A dataset passes only if both hold; anything else fails or is reported '
                           'as schema_mismatch when columns differ from the FeCO adapter contract.',
        'no_retrofit': 'If any model form or threshold were changed after seeing data, the run must '
                       'be labeled retrospective.'}
    PROTOCOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    PROTOCOL_PATH.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
    print(json.dumps({'protocol': str(PROTOCOL_PATH),
        'sha256': hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest()}, indent=2))


def download():
    """Fetch the four preregistered files with token auth and hash receipts."""
    from experiments.public_data import retrieve, dryad_auth_headers, ROOT
    catalog = json.loads(Path('data/physiology_raw/feco-catalog.json').read_text(encoding='utf-8'))
    headers = dryad_auth_headers()
    if not headers:
        raise SystemExit('DRYAD_API_TOKEN required')
    results = []
    for f in catalog['files']:
        if f['path'] not in FILES:
            continue
        record = retrieve('https://datadryad.org'+f['_links']['stash:download']['href'],
                          ROOT/'feco'/f['path'],
                          f['digest'] if f['digestType'] == 'sha-256' else None,
                          f['size'], headers=headers)
        results.append({'file': f['path'], 'status': record['status']})
        print(f['path'], record['status'], flush=True)
    return results


def _predictions(name, angle, rate_hz):
    angle = np.asarray(angle, dtype=float)
    if name.startswith('hook_flexion'):
        dx = np.diff(angle)*rate_hz
        dx = np.r_[dx[0], dx]
        active = (dx < -50.).astype(float)
    elif name.startswith('hook_extension'):
        dx = np.diff(angle)*rate_hz
        dx = np.r_[dx[0], dx]
        active = (dx > 50.).astype(float)
    elif name.startswith('club'):
        dx = np.abs(np.diff(angle)*rate_hz)
        active = np.r_[dx[0], dx]
    else:  # claw tonic position: identity transform
        return angle.copy()
    t = np.linspace(0, len(angle)/rate_hz, len(angle))
    kernel = np.exp(-t/.30)-np.exp(-t/.03)
    kernel /= kernel.sum()
    from scipy.signal import fftconvolve
    return fftconvolve(active, kernel)[:len(angle)]


def evaluate():
    if not PROTOCOL_PATH.exists():
        raise SystemExit('Register before evaluating')
    from experiments.feco import split_animals, validate_frame
    import pandas as pd
    protocol = json.loads(PROTOCOL_PATH.read_text(encoding='utf-8'))
    report = {'protocol_sha256': hashlib.sha256(PROTOCOL_PATH.read_bytes()).hexdigest(),
              'evaluated_at': datetime.now(timezone.utc).isoformat(),
              'datasets': {}, 'biological_acceptance': False}
    for name in FILES:
        path = Path('data/physiology_raw/feco')/name
        receipt = path.with_suffix(path.suffix+'.receipt.json')
        if not path.exists() or not receipt.exists():
            report['datasets'][name] = {'status': 'not_available'}
            continue
        receipt_data = json.loads(receipt.read_text(encoding='utf-8'))
        if not receipt_data.get('publisher_sha256_verified'):
            report['datasets'][name] = {'status': 'unverified_file'}
            continue
        try:
            frame = pd.read_parquet(path, columns=['animal_id', 'trial', 'time', 'calcium',
                                                   'L1C_flex', 'L1C_flex_vel', 'analyze'])
            validate_frame(frame)
        except Exception as error:
            report['datasets'][name] = {'status': 'schema_mismatch', 'error': type(error).__name__+': '+str(error)[:200]}
            continue
        try:
            split = split_animals(frame.animal_id)
        except ValueError as error:
            report['datasets'][name] = {'status': 'insufficient_animals_for_registered_split',
                                        'animals': int(frame.animal_id.nunique()),
                                        'error': str(error)}
            continue
        groups = []
        for (animal, trial), part in frame.groupby(['animal_id', 'trial'], observed=True, sort=False):
            dt = np.diff(part.time.to_numpy())
            rate = 1/np.median(dt)
            prediction = _predictions(name, part.L1C_flex.to_numpy(), rate)
            use = part.analyze.eq(1).to_numpy() & np.isfinite(part.calcium.to_numpy())
            groups.append({'split': split[str(animal)], 'x': prediction[use],
                           'y': part.calcium.to_numpy()[use]})
        train = [g for g in groups if g['split'] == 'train' and len(g['x'])]
        if not train or not any(g['split'] == 'test' and len(g['x']) for g in groups):
            report['datasets'][name] = {'status': 'insufficient_split'}
            continue
        x = np.concatenate([g['x'] for g in train]); y = np.concatenate([g['y'] for g in train])
        gain, offset = np.linalg.lstsq(np.c_[x, np.ones_like(x)], y, rcond=None)[0]
        baseline = float(y.mean())
        wins, model_mse, base_mse, n_test = 0, 0., 0., 0
        test_total = 0
        for g in groups:
            if g['split'] != 'test' or not len(g['x']):
                continue
            error = gain*g['x']+offset-g['y']
            const = baseline-g['y']
            wins += int(float(np.mean(error**2)) < float(np.mean(const**2)))
            model_mse += float(np.sum(error**2)); base_mse += float(np.sum(const**2))
            n_test += len(error)
            test_total += 1
        passed = test_total > 0 and wins/test_total > THRESHOLD['majority_of_test_trials'] \
            and model_mse < base_mse
        report['datasets'][name] = {'status': 'evaluated', 'gain': float(gain), 'offset': float(offset),
            'test_trials_won': wins, 'test_trials_total': test_total,
            'pooled_test_mse': model_mse/n_test if n_test else None,
            'pooled_baseline_mse': base_mse/n_test if n_test else None,
            'passed': bool(passed)}
    Path('validation/feco/prospective-results.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk in ('status', 'passed', 'test_trials_won', 'test_trials_total')}
                      for k, v in report['datasets'].items()}, indent=2))
    return report


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'register'
    if mode == 'register':
        register()
    elif mode == 'download':
        download()
    elif mode == 'evaluate':
        evaluate()
    else:
        raise SystemExit('modes: register|download|evaluate')
