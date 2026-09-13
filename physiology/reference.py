"""Graded conductance reference. Units: ms, mV, pF, nS, pA.

Each edge has an explicitly supplied postsynaptic reversal potential. Unknown
transmitters cannot silently become excitatory. All defaults are engineering
fixtures, not measured MaleCNS physiology.
"""
from dataclasses import dataclass
import copy
import hashlib
import json
import numpy as np


@dataclass(frozen=True)
class Parameters:
    capacitance_pf: float = 10.
    leak_ns: float = 1.
    resting_mv: float = -60.
    synapse_tau_ms: float = 5.
    adaptation_tau_ms: float = 100.
    adaptation_ns: float = .1

    def __post_init__(self):
        for key,value in vars(self).items():
            a = np.asarray(value,dtype=float)
            if a.ndim > 1 or not np.isfinite(a).all():
                raise ValueError('Parameters must be finite scalars or neuron vectors')
            if key in ['capacitance_pf','leak_ns','synapse_tau_ms','adaptation_tau_ms'] and np.any(a<=0):
                raise ValueError('Positive passive parameter required')
            if key == 'adaptation_ns' and np.any(a<0):
                raise ValueError('Nonnegative adaptation required')
            if a.ndim:
                a = a.copy(); a.flags.writeable=False
                object.__setattr__(self,key,a)


class ConductanceNetwork:
    def __init__(self, n, pre, post, conductance_ns, reversal_mv, delay_ms,
                 dt_ms=.1, parameters=None, individuals=1):
        if n < 1 or individuals < 1 or not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('Invalid size or time step')
        self.n, self.individuals, self.dt_ms = n, individuals, float(dt_ms)
        self.parameters = parameters or Parameters()
        for key,value in vars(self.parameters).items():
            if np.shape(value) not in [(),(n,)]:
                raise ValueError('Parameter does not match neuron set: '+key)
        self.pre, self.post = np.array(pre, dtype=np.int64), np.array(post, dtype=np.int64)
        self.gbar, self.reversal = np.array(conductance_ns, dtype=float), np.array(reversal_mv, dtype=float)
        delay = np.array(delay_ms, dtype=float)
        if any(a.ndim != 1 or a.shape != self.pre.shape for a in [self.pre,self.post,self.gbar,self.reversal,delay]):
            raise ValueError('Edge arrays must align')
        if any(not np.isfinite(a).all() for a in [self.gbar,self.reversal,delay]) or np.any(self.gbar < 0) or np.any(delay < 0):
            raise ValueError('Explicit finite conductance, receptor reversal and delay required')
        if np.any(self.pre < 0) or np.any(self.pre >= n) or np.any(self.post < 0) or np.any(self.post >= n):
            raise ValueError('Edge outside neuron set')
        self.delay_ticks = np.rint(delay/self.dt_ms).astype(np.int64)
        if not np.allclose(self.delay_ticks*self.dt_ms, delay, atol=1e-10, rtol=0):
            raise ValueError('Delays must be integer multiples of dt')
        for a in [self.pre,self.post,self.gbar,self.reversal,self.delay_ticks]:
            a.flags.writeable = False
        self.v = np.full((individuals,n), self.parameters.resting_mv)
        self.adaptation = np.zeros_like(self.v)
        self.g = np.zeros((individuals,len(self.pre)))
        self.efficacy = np.ones_like(self.g)
        self.history = np.zeros((int(self.delay_ticks.max(initial=0))+1,individuals,n))
        self.ticks = 0
        fingerprint = hashlib.sha256(json.dumps({'n':n,'individuals':individuals,
            'dt_ms':self.dt_ms,'parameters':{k:np.asarray(v).tolist() for k,v in vars(self.parameters).items()}},sort_keys=True).encode())
        for a in [self.pre,self.post,self.gbar,self.reversal,self.delay_ticks]:
            fingerprint.update(a.tobytes())
        self.fingerprint = fingerprint.hexdigest()

    def step(self, current_pa):
        current = np.asarray(current_pa, dtype=float)
        if current.shape != self.v.shape or not np.isfinite(current).all():
            raise ValueError('Current must have shape (individuals, neurons), in pA')
        p, dt = self.parameters, self.dt_ms
        # Piecewise linear graded release is a declared calibration hypothesis.
        self.history[self.ticks % len(self.history)] = np.clip((self.v-p.resting_mv)/20., 0., 1.)
        slots = (self.ticks-self.delay_ticks) % len(self.history)
        release = self.history[slots, :, self.pre].T
        target_g = self.gbar[None,:]*self.efficacy*release
        tau = np.asarray(p.synapse_tau_ms)
        edge_tau = tau if tau.ndim==0 else tau[self.post]
        self.g += -np.expm1(-dt/edge_tau)*(target_g-self.g)
        for i in range(self.individuals):
            total = np.bincount(self.post, weights=self.g[i], minlength=self.n)+p.leak_ns
            drive = np.bincount(self.post, weights=self.g[i]*self.reversal, minlength=self.n)
            equilibrium = (drive+p.leak_ns*p.resting_mv+current[i]-self.adaptation[i])/total
            self.v[i] = equilibrium+(self.v[i]-equilibrium)*np.exp(-dt*total/p.capacitance_pf)
        self.adaptation += -np.expm1(-dt/p.adaptation_tau_ms)*(p.adaptation_ns*(self.v-p.resting_mv)-self.adaptation)
        self.ticks += 1
        if not np.isfinite(self.v).all():
            raise FloatingPointError('Nonfinite voltage')
        return self.v.copy()

    def snapshot(self):
        return copy.deepcopy({'fingerprint':self.fingerprint, 'ticks':self.ticks, 'v':self.v, 'adaptation':self.adaptation,
            'g':self.g, 'efficacy':self.efficacy, 'history':self.history})

    def restore(self, state):
        if state.get('fingerprint') != self.fingerprint:
            raise ValueError('Checkpoint topology, parameters or clock differ')
        arrays = {}
        for key in ['v','adaptation','g','efficacy','history']:
            a = np.asarray(state[key], dtype=float)
            if a.shape != getattr(self,key).shape or not np.isfinite(a).all():
                raise ValueError('Invalid checkpoint '+key)
            arrays[key] = a.copy()
        if not isinstance(state['ticks'], int) or state['ticks'] < 0:
            raise ValueError('Invalid clock')
        if np.any(arrays['g'] < 0) or np.any(arrays['efficacy'] < 0):
            raise ValueError('Invalid synaptic state')
        for key,a in arrays.items():
            setattr(self,key,a)
        self.ticks = state['ticks']
