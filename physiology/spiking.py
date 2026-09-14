"""Adaptive exponential integrate-and-fire point neurons. Units: ms, mV, pF, nS, pA.

C dV/dt = -gL(V-EL) + gL*slope*exp((V-VT)/slope) - w + I
tau_w dw/dt = a*(V-EL) - w; on spike V<-reset, w<-w+b

Spikes are threshold-crossing events with explicit reset and refractory state,
replacing graded release only where spike coding is the declared hypothesis.
Parameters must come from priors or measurement; defaults here are software
fixtures, never measured MaleCNS physiology.
"""
from dataclasses import dataclass
import copy
import hashlib
import json
import numpy as np


@dataclass(frozen=True)
class AdExParameters:
    capacitance_pf: float = 10.
    leak_ns: float = 1.
    resting_mv: float = -60.
    rheobase_mv: float = -50.
    slope_mv: float = 2.
    reset_mv: float = -65.
    refractory_ms: float = 2.
    adaptation_ns: float = .1
    adaptation_tau_ms: float = 100.
    spike_increment_pa: float = 5.

    def __post_init__(self):
        for key, value in vars(self).items():
            a = np.asarray(value, dtype=float)
            if a.ndim > 1 or not np.isfinite(a).all():
                raise ValueError('Parameters must be finite scalars or neuron vectors')
            if key in ['capacitance_pf', 'leak_ns', 'slope_mv', 'refractory_ms', 'adaptation_tau_ms'] and np.any(a <= 0):
                raise ValueError('Positive ' + key + ' required')
            if key in ['adaptation_ns', 'spike_increment_pa'] and np.any(a < 0):
                raise ValueError('Nonnegative ' + key + ' required')
            if a.ndim:
                a = a.copy()
                a.flags.writeable = False
                object.__setattr__(self, key, a)


class SpikingNetwork:
    """Deterministic event layer; synaptic delivery is the caller's explicit model."""

    def __init__(self, n, parameters=None, dt_ms=.1, individuals=1):
        if n < 1 or individuals < 1 or not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('Invalid size or time step')
        self.n, self.individuals, self.dt_ms = n, individuals, float(dt_ms)
        self.parameters = parameters or AdExParameters()
        for key, value in vars(self.parameters).items():
            if np.shape(value) not in [(), (n,)]:
                raise ValueError('Parameter does not match neuron set: ' + key)
        p = self.parameters
        self.refractory_ticks = np.maximum(
            np.rint(np.broadcast_to(np.asarray(p.refractory_ms, dtype=float), (n,))/dt_ms).astype(np.int64), 1)
        resting = np.broadcast_to(np.asarray(p.resting_mv, dtype=float), (n,)).astype(float)
        self.v = np.tile(resting, (individuals, 1))
        self.w = np.zeros((individuals, n))
        self.spikes = np.zeros((individuals, n), dtype=bool)
        # Saturating counter avoids int64 overflow at the "never fired" sentinel.
        self.since_spike = np.full((individuals, n), 1 << 62, dtype=np.int64)
        self.total_spikes = np.zeros((individuals, n), dtype=np.int64)
        self.ticks = 0
        fingerprint = hashlib.sha256(json.dumps({'n': n, 'individuals': individuals, 'dt_ms': dt_ms,
            'parameters': {k: np.asarray(v).tolist() for k, v in vars(self.parameters).items()}}, sort_keys=True).encode())
        self.fingerprint = fingerprint.hexdigest()

    def _broadcast(self, value):
        return np.broadcast_to(np.asarray(value, dtype=float), self.v.shape)

    def step(self, current_pa):
        current = np.asarray(current_pa, dtype=float)
        if current.shape != self.v.shape or not np.isfinite(current).all():
            raise ValueError('Current must have shape (individuals, neurons), in pA')
        p, dt = self.parameters, self.dt_ms
        capacitance = self._broadcast(p.capacitance_pf)
        active = self.since_spike >= self.refractory_ticks
        exponent = np.clip((self.v-self._broadcast(p.rheobase_mv))/self._broadcast(p.slope_mv), -50, 50)
        dv = (-self._broadcast(p.leak_ns)*(self.v-self._broadcast(p.resting_mv))
              + self._broadcast(p.leak_ns)*self._broadcast(p.slope_mv)*np.exp(exponent)
              - self.w + current)/(capacitance/dt)
        v_new = self.v+dv*active
        w_target = self._broadcast(p.adaptation_ns)*(v_new-self._broadcast(p.resting_mv))
        w_new = self.w+(-np.expm1(-dt/self._broadcast(p.adaptation_tau_ms)))*(w_target-self.w)
        fired = (v_new >= self._broadcast(p.rheobase_mv)) & active
        if fired.any():
            v_new = np.where(fired, self._broadcast(p.reset_mv), v_new)
            w_new = w_new+np.where(fired, self._broadcast(p.spike_increment_pa), 0.)
            self.since_spike = np.where(fired, 0, self.since_spike)
            self.total_spikes += fired
        self.since_spike = np.minimum(self.since_spike+1, 1 << 62)
        self.v, self.w, self.spikes = v_new, w_new, fired
        self.ticks += 1
        if not np.isfinite(self.v).all():
            raise FloatingPointError('Nonfinite voltage')
        return self.v.copy()

    def snapshot(self):
        return copy.deepcopy({'fingerprint': self.fingerprint, 'ticks': self.ticks, 'v': self.v,
            'w': self.w, 'since_spike': self.since_spike, 'total_spikes': self.total_spikes})

    def restore(self, state):
        if state.get('fingerprint') != self.fingerprint:
            raise ValueError('Checkpoint parameters or clock differ')
        for key in ['v', 'w']:
            a = np.asarray(state[key], dtype=float)
            if a.shape != getattr(self, key).shape or not np.isfinite(a).all():
                raise ValueError('Invalid checkpoint '+key)
            setattr(self, key, a.copy())
        since = np.asarray(state['since_spike'], dtype=np.int64)
        total = np.asarray(state['total_spikes'], dtype=np.int64)
        if since.shape != self.since_spike.shape or np.any(since < 0) or total.shape != self.total_spikes.shape or np.any(total < 0):
            raise ValueError('Invalid refractory or event checkpoint')
        if not isinstance(state['ticks'], int) or state['ticks'] < 0:
            raise ValueError('Invalid clock')
        self.since_spike, self.total_spikes = since, total
        self.ticks = state['ticks']
