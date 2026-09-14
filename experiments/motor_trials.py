"""Extract passive properties and rheobase from Azevedo current-step trials.

Reads CurrentStep2T_Raw_* entries from a publisher-hash-verified session zip,
measures per-trial subthreshold steady-state deflection, and derives input
resistance and rheobase. The session notes identify the driver line, so the
recorded cell carries its published class identity. Traces are in natural
units (mV, pA) at 10 kHz per the dataset README. Results are calibration
inputs for the reviewed motor circuit, not MaleCNS physiology by themselves.
Run: python -m experiments.motor_trials
"""
import io
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.io import loadmat

SAMPRATE = 10_000
PRE_S, STIM_S, SWEEP_S = .12, .2, .42
DRIVER_CLASS = {'22a08': 'intermediate flexor MN (R22A08-Gal4, BDSC 47902)',
                '81a07': 'fast flexor MN (R81A07-Gal4, BDSC 40100)',
                '35c09': 'slow flexor MN (R35C09-Gal4, BDSC 49901)',
                '81a06': 'other flexor line (R81A06-Gal4)',
                '81a04': 'other flexor line (R81A04-Gal4)'}
DRIVER_SOURCE = 'Azevedo et al. 2020 eLife 9:e56754, Fig 4-fig supp 1 driver list'


def driver_identity(z):
    """Parse the driver line tag from the session notes; identity is per notes, not inferred."""
    notes = [n for n in z.namelist() if re.match(r'notes_.*\.txt$', n)]
    if not notes:
        return None, None, None
    text = z.read(notes[0]).decode('utf-8', errors='replace')
    match = re.search(r'-\s*\d\d:\d\d:\d\d\s*-\s*([0-9a-z]{5});', text.splitlines()[0], re.I)
    tag = match.group(1).lower() if match else None
    return tag, DRIVER_CLASS.get(tag, 'unmapped driver line: '+str(tag)), notes[0]


def seal_resistance_gohm(z):
    """Voltage-clamp seal/leak pulses: seal quality metric, NOT cell input resistance."""
    names = [n for n in z.namelist() if re.match(r'SealAndLeak_Raw_.*\.mat$', n)]
    if not names:
        return None
    d = loadmat(io.BytesIO(z.read(sorted(names)[0])))
    if 'current' not in d or 'voltage' not in d:
        return None
    current = np.asarray(d['current'], dtype=float).ravel()
    voltage = np.asarray(d['voltage'], dtype=float).ravel()
    middle = np.median(voltage)
    step_v = float(np.median(voltage[voltage > middle])-np.median(voltage[voltage <= middle]))
    delta_i = float(np.median(current[voltage > middle])-np.median(current[voltage <= middle]))
    if delta_i == 0:
        return None
    return step_v/delta_i  # mV / pA -> GOhm


def trial_metrics(voltage, current, step_pa):
    voltage = np.asarray(voltage, dtype=float).ravel()
    current = np.asarray(current, dtype=float).ravel()
    pre = slice(0, int(PRE_S*SAMPRATE))
    stim_end = int((PRE_S+STIM_S)*SAMPRATE)
    steady = slice(stim_end-int(.05*SAMPRATE), stim_end)
    baseline, steady_v = float(voltage[pre].mean()), float(voltage[steady].mean())
    stim_window = voltage[int(PRE_S*SAMPRATE):stim_end]
    peak = float(stim_window.max())
    spiked = peak > baseline+20.  # mV-scale traces: 20 mV above baseline
    return {'baseline_mv': baseline, 'steady_mv': steady_v,
            'delta_mv': steady_v-baseline, 'step_pa': float(step_pa),
            'peak_mv': peak, 'spiked': bool(spiked)}


def analyze(zip_path):
    z = zipfile.ZipFile(zip_path)
    raw_names = sorted([n for n in z.namelist()
                        if re.match(r'CurrentStep2T_Raw_.*_(\d+)\.mat$', n)],
                       key=lambda n: int(re.search(r'_(\d+)\.mat$', n).group(1)))
    trials = []
    for name in raw_names:
        d = loadmat(io.BytesIO(z.read(name)))
        if int(d['excluded'][0, 0]):
            continue
        params = d['params'][0, 0]
        step = float(np.asarray(params['step']).ravel()[0])
        trial = int(np.asarray(params['trial']).ravel()[0])
        metrics = trial_metrics(d['voltage_1'], d['current_1'], step)
        metrics['trial'] = trial
        metrics['name'] = str(d['name'][0])
        trials.append(metrics)
    # Input resistance from subthreshold steps: least-squares slope when at least
    # two subthreshold step levels exist, otherwise the single-step estimate.
    subthreshold = [t for t in trials if not t['spiked']]
    steps = np.array([t['step_pa'] for t in subthreshold])
    deltas = np.array([t['delta_mv'] for t in subthreshold])
    unique_steps = np.unique(steps)
    if len(unique_steps) >= 2:
        slope_mv_per_pa = float(np.polyfit(steps, deltas, 1)[0])
        method = 'least-squares slope over subthreshold steps'
    elif len(unique_steps) == 1:
        slope_mv_per_pa = float(deltas.mean()/steps.mean())
        method = 'single subthreshold step (%.1f pA, n=%d trials)' % (steps.mean(), len(steps))
    else:
        slope_mv_per_pa, method = None, 'no subthreshold trials'
    spiked = [t for t in trials if t['spiked']]
    rheobase_pa = min((t['step_pa'] for t in spiked), default=None)
    return {'trials': trials, 'n_trials': len(trials),
            'n_excluded': len(raw_names)-len(trials),
            'resting_mv': float(np.mean([t['baseline_mv'] for t in trials])),
            'subthreshold_slope_mv_per_pa': slope_mv_per_pa,
            'input_resistance_mohm': slope_mv_per_pa*1e3 if slope_mv_per_pa else None,
            'rin_method': method,
            'rheobase_pa': rheobase_pa,
            'voltage_unit_note': 'voltage_1 traces are in mV (session resting mean lands in the '
                                 'biological MN range), current in pA, '
                                 f'{SAMPRATE} Hz, sweep {SWEEP_S} s (pre {PRE_S}, stim {STIM_S})'}


def main():
    import pandas as pd
    zip_path = Path('data/physiology_raw/motor/180222_F1_C1.zip')
    receipt = json.loads(zip_path.with_suffix('.zip.receipt.json').read_text())
    if not receipt.get('publisher_sha256_verified'):
        raise ValueError('Publisher-verified trial data required')
    z = zipfile.ZipFile(zip_path)
    tag, identity, notes_name = driver_identity(z)
    seal = seal_resistance_gohm(z)
    result = analyze(zip_path)
    pd.DataFrame(result['trials']).to_parquet(
        'data/physiology_raw/motor/current_step_trials_180222_F1_C1.parquet', index=False)
    report = {'scope': 'passive properties from one verified Azevedo ephys session',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source': str(zip_path), 'source_sha256': receipt['sha256'],
        'driver_tag': tag, 'cell_identity': identity, 'identity_source': DRIVER_SOURCE,
        'notes_file': notes_name,
        'n_trials': result['n_trials'], 'n_excluded_by_author': result['n_excluded'],
        'resting_mv': result['resting_mv'],
        'subthreshold_slope_mv_per_pa': result['subthreshold_slope_mv_per_pa'],
        'input_resistance_mohm': result['input_resistance_mohm'],
        'seal_resistance_gohm': seal,
        'rin_method': result['rin_method'],
        'rheobase_pa': result['rheobase_pa'],
        'units': result['voltage_unit_note'],
        'caveats': ['Single animal/session of one driver-identified cell',
                    'Class means in the paper (intermediate Rin ~300 MOhm, Vrest ~-60 mV) differ from '
                    'this single cell; per-cell variance is expected and reported as measured',
                    'SealAndLeak estimate is a pulse-median approximation, not the authors\' full pipeline'],
        'biological_acceptance': False}
    Path('validation/motor-trial-analysis.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({k: report[k] for k in ['driver_tag', 'cell_identity', 'n_trials', 'resting_mv',
        'input_resistance_mohm', 'seal_resistance_gohm', 'rheobase_pa']}, indent=2))
    return report


if __name__ == '__main__':
    main()
