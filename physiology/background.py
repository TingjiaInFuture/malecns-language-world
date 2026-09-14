"""Seeded background activity current. Units: ms, pA, ohm-free.

Ornstein-Uhlenbeck colored noise per neuron with an explicit seed, amplitude
and time constant. Reproducibility is the point: the same seed and inputs give
bit-identical currents, so controlled noise never hides as run-to-run drift.
Amplitudes are calibration inputs; defaults are software fixtures.
"""
import numpy as np


class BackgroundCurrent:
    def __init__(self, n_neurons, tau_ms, sigma_pa, seed):
        if not isinstance(n_neurons, int) or n_neurons < 1 \
                or not np.isfinite([tau_ms, sigma_pa]).all() or tau_ms <= 0 or sigma_pa < 0:
            raise ValueError('Positive size and tau, nonnegative sigma required')
        self.tau_ms, self.sigma_pa, self.n_neurons = float(tau_ms), float(sigma_pa), n_neurons
        self.rng = np.random.default_rng(seed)
        self.state = np.zeros(n_neurons)

    def step(self, dt_ms):
        if not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('Positive time step required')
        decay = np.exp(-dt_ms/self.tau_ms)
        noise = np.sqrt(1.-decay**2)*self.sigma_pa
        self.state = self.state*decay+self.rng.normal(0., noise, self.n_neurons)
        return self.state.copy()

    def snapshot(self):
        return {'state': self.state.copy(),
                'bit_generator_state': self.rng.bit_generator.state}

    def restore(self, state):
        stored = np.asarray(state['state'], dtype=float)
        if stored.shape != (self.n_neurons,) or not np.isfinite(stored).all():
            raise ValueError('Invalid background checkpoint')
        self.state = stored.copy()
        self.rng.bit_generator.state = state['bit_generator_state']
