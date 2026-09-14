"""Sleep/wake and circadian state with explicit units. Hours for the clock.

A delayed negative-feedback oscillator produces a tunable ~24 h rhythm that
drives an arousal gate. The gate only scales reviewed channels (sensory gains,
modulator pools); it never selects actions. Constants are software fixtures
until animal-calibrated; period is an explicit constructor input.
"""
import numpy as np


class CircadianClock:
    """Two-variable relaxation oscillator; phase advances deterministically."""

    def __init__(self, period_h, hours_per_step, amplitude_nM=1.):
        if not np.isfinite([period_h, hours_per_step, amplitude_nM]).all() \
                or period_h <= 0 or hours_per_step <= 0 or amplitude_nM <= 0:
            raise ValueError('Positive period, step and amplitude required')
        self.period_h = float(period_h)
        self.dt_h = float(hours_per_step)
        self.amplitude_nM = float(amplitude_nM)
        self.phase_h = 0.
        self.ticks = 0

    def step(self):
        self.phase_h = (self.phase_h+self.dt_h) % self.period_h
        self.ticks += 1
        return self.concentration_nm()

    def concentration_nm(self):
        # First harmonic of the molecular clock; engineering reference shape.
        return self.amplitude_nM*(0.5+0.5*np.sin(2*np.pi*self.phase_h/self.period_h))

    def snapshot(self):
        return {'period_h': self.period_h, 'dt_h': self.dt_h, 'phase_h': self.phase_h, 'ticks': self.ticks}

    def restore(self, state):
        if state['period_h'] != self.period_h or state['dt_h'] != self.dt_h \
                or not 0 <= state['phase_h'] < self.period_h or not isinstance(state['ticks'], int):
            raise ValueError('Incompatible or invalid clock checkpoint')
        self.phase_h, self.ticks = float(state['phase_h']), state['ticks']


class ArousalGate:
    """Maps clock concentration plus homeostatic sleep pressure to a gain factor."""

    def __init__(self, wake_threshold_nM, sleep_pressure_tau_h, bounds):
        lo, hi = (float(x) for x in bounds)
        if not np.isfinite([wake_threshold_nM, sleep_pressure_tau_h, lo, hi]).all() \
                or wake_threshold_nM < 0 or sleep_pressure_tau_h <= 0 or not 0 < lo < hi:
            raise ValueError('Threshold, time constant and 0 < lower < upper required')
        self.wake_threshold_nM = float(wake_threshold_nM)
        self.tau_h = float(sleep_pressure_tau_h)
        self.lower, self.upper = lo, hi
        self.sleep_pressure = 0.

    def step(self, clock_concentration_nm, dt_h):
        if not np.isfinite(clock_concentration_nm) or clock_concentration_nm < 0 \
                or not np.isfinite(dt_h) or dt_h <= 0:
            raise ValueError('Nonnegative clock concentration and positive step required')
        awake = clock_concentration_nm >= self.wake_threshold_nM
        target = 0. if awake else 1.
        self.sleep_pressure += -np.expm1(-dt_h/self.tau_h)*(target-self.sleep_pressure)
        return self.gain()

    def gain(self):
        return self.lower+(self.upper-self.lower)*(1.-self.sleep_pressure)
