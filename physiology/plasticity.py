"""Opt-in local eligibility rule for explicitly reviewed synapses.

This equation is an engineering hypothesis, not a whole-brain STDP model.
Structural counts and conductance priors remain untouched.
"""
import numpy as np


class ModulatedEligibility:
    def __init__(self, shape, allowed, evidence, tau_ms, rate_per_ms, bounds=(.1, 3.)):
        self.allowed = np.array(allowed, dtype=bool)
        if self.allowed.shape != (shape[-1],) or not evidence or tau_ms <= 0 or rate_per_ms < 0:
            raise ValueError('Explicit circuit mask, evidence and valid kinetics required')
        if not all(np.isfinite(x) for x in [tau_ms,rate_per_ms,*bounds]) or not 0 <= bounds[0] < bounds[1]:
            raise ValueError('Invalid learning bounds')
        self.evidence, self.tau, self.rate, self.bounds = evidence, tau_ms, rate_per_ms, bounds
        self.trace = np.zeros(shape)

    def step(self, efficacy, pre_release, post_response, modulator, dt_ms):
        arrays = [np.asarray(a,dtype=float) for a in [efficacy,pre_release,post_response,modulator]]
        if any(a.shape != self.trace.shape or not np.isfinite(a).all() for a in arrays) or not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('Invalid local learning input')
        w,pre,post,mod = arrays
        self.trace += -np.expm1(-dt_ms/self.tau)*(pre*post-self.trace)
        updated = w.copy()
        updated[:,self.allowed] = np.clip((w+self.rate*dt_ms*mod*self.trace)[:,self.allowed],*self.bounds)
        return updated
