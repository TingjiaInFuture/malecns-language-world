"""Literature-parameterized motor-unit prediction test (spiking -> force).

Classes use Azevedo et al. 2020 (eLife 9:e56754) female flexor measurements:
Rin 150/300/700 MOhm and Vrest -68/-60/-48 mV for fast/intermediate/slow, force
per spike ~10/1/<0.1 uN, spontaneous slow ~30 Hz. Qualitative predictions
reproduced here are about the model stack's mechanics, not a validation of male
MaleCNS physiology. Run: python -m experiments.motor_unit_prediction
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from physiology.spiking import AdExParameters, SpikingNetwork
from body.recruitment import MotorUnit, MotorUnitPool

CLASSES = {
    'slow': {'leak_ns': 1/0.7, 'resting_mv': -48., 'force_per_spike_un': 0.013, 'relaxation_tau_ms': 100.},
    'intermediate': {'leak_ns': 1/0.3, 'resting_mv': -60., 'force_per_spike_un': 1., 'relaxation_tau_ms': 40.},
    'fast': {'leak_ns': 1/0.15, 'resting_mv': -68., 'force_per_spike_un': 10., 'relaxation_tau_ms': 20.},
}
SOURCE = 'Azevedo et al. 2020, eLife 9:e56754 (female 1-4 dpe); Rin 150-700 MOhm, Vrest -68..-48 mV, force/spike 10/1/0.013 uN'


def run(drive_pa=45., dt_ms=.1, duration_ms=1500.):
    units, traces = [], {}
    for name, spec in CLASSES.items():
        parameters = AdExParameters(leak_ns=spec['leak_ns'], resting_mv=spec['resting_mv'],
                                    rheobase_mv=spec['resting_mv']+10., capacitance_pf=10.,
                                    refractory_ms=2.)
        net = SpikingNetwork(1, parameters, dt_ms=dt_ms)
        spikes = 0
        for _ in range(int(duration_ms/dt_ms)):
            net.step([[drive_pa]])
            spikes = int(net.total_spikes[0, 0])
        traces[name] = {'spikes': spikes,
                        'rate_hz': spikes/(duration_ms/1000.),
                        'rheobase_offset_mv': parameters.rheobase_mv}
        units.append(MotorUnit({'slow': 1, 'intermediate': 2, 'fast': 3}[name],
                               'tibia_flexor', 10. if name == 'slow' else 30. if name == 'intermediate' else 60.,
                               spec['force_per_spike_un'], spec['relaxation_tau_ms'], SOURCE))
    pool = MotorUnitPool(units)
    per_class_rate = np.array([traces[k]['rate_hz'] for k in ['slow', 'intermediate', 'fast']])
    forces = []
    for _ in range(int(500/dt_ms)):
        forces.append(pool.step(per_class_rate, dt_ms)['tibia_flexor'])
    slow_first = pool.order()[0] == 1
    report = {'scope': 'software stack check against female literature class values; not male physiology',
        'created_at': datetime.now(timezone.utc).isoformat(),
        'source': SOURCE,
        'drive_pa': drive_pa, 'duration_ms': duration_ms,
        'class_traces': traces,
        'steady_force_un': forces[-1],
        'force_range_un': [float(min(forces)), float(max(forces))],
        'predictions': {
            'slow_units_recruit_first': bool(slow_first),
            'slow_tonic_activity': bool(traces['slow']['rate_hz'] > 5.),
            'fast_larger_per_spike_force': CLASSES['fast']['force_per_spike_un'] > 100*CLASSES['slow']['force_per_spike_un']},
        'caveats': ['Female-measured parameters; male transfer is a hypothesis',
                    'Rheobase offsets, capacitance, refractory period and recruitment thresholds (10/30/60 Hz) '
                    'are engineering fixtures; measured thresholds and per-body-id class assignment are pending'],
        'biological_acceptance': False,
        'executed_source_sha256': {'experiments/motor_unit_prediction.py':
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    Path('validation/motor-unit-prediction.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({'class_traces': traces, 'steady_force_un': forces[-1],
                      'predictions': report['predictions']}, indent=2))
    return report


if __name__ == '__main__':
    run()
