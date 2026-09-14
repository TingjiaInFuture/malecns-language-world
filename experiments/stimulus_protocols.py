"""Preregistrable stimulus protocols with explicit units. ms, pA, deg, mol/m^3.

A protocol is data, not behavior: it describes what is delivered to named
channels. Duration/shape/seed are frozen at construction and hashed so a report
can reference an immutable stimulus identity.
"""
import hashlib
import json

import numpy as np

SHAPES = ('step', 'ramp', 'pulse_train', 'white_noise')


def waveform(shape, n_steps, amplitude, seed=0):
    if shape not in SHAPES:
        raise ValueError('Unknown stimulus shape ' + str(shape))
    if not isinstance(n_steps, int) or n_steps < 1 or not np.isfinite(amplitude):
        raise ValueError('Positive sample count and finite amplitude required')
    if shape == 'step':
        return np.full(n_steps, amplitude, dtype=float)
    if shape == 'ramp':
        return np.linspace(0., amplitude, n_steps)
    if shape == 'pulse_train':
        values = np.zeros(n_steps)
        values[::5] = amplitude
        return values
    rng = np.random.default_rng(seed)
    return rng.normal(0., abs(amplitude), n_steps)


class CurrentProtocol:
    """Injection into explicit neuron indices; observers cannot mutate it."""

    def __init__(self, neuron_indices, dt_ms, shape, duration_ms, amplitude_pa, seed=0):
        indices = np.asarray(neuron_indices, dtype=np.int64)
        if indices.ndim != 1 or not len(indices) or np.any(indices < 0):
            raise ValueError('Nonnegative neuron indices required')
        steps = int(round(duration_ms/dt_ms))
        if steps < 1 or not np.isclose(steps*dt_ms, duration_ms, rtol=0, atol=1e-9):
            raise ValueError('Duration must be an integer number of time steps')
        self.neuron_indices = indices
        self.dt_ms, self.duration_ms, self.shape = float(dt_ms), float(duration_ms), shape
        self.amplitude_pa, self.seed = float(amplitude_pa), int(seed)
        self.samples = waveform(shape, steps, amplitude_pa, seed)
        self.fingerprint = hashlib.sha256(json.dumps({'indices': indices.tolist(), 'dt_ms': dt_ms,
            'shape': shape, 'duration_ms': duration_ms, 'amplitude_pa': amplitude_pa,
            'seed': seed, 'waveform_sha256': hashlib.sha256(self.samples.tobytes()).hexdigest()},
            sort_keys=True).encode()).hexdigest()

    def current_pa(self, n_neurons, step_index):
        if not isinstance(step_index, int) or not 0 <= step_index < len(self.samples):
            raise ValueError('Step index inside the protocol required')
        current = np.zeros(n_neurons)
        current[self.neuron_indices] = self.samples[step_index]
        return current
