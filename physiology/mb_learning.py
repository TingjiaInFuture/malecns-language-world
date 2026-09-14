"""Mushroom-body-compartment local plasticity gated by dopamine. Units: ms, nM.

Evidence scope: compartment-specific presynaptic plasticity is heterogeneous
(Dopamine-Dependent Plasticity ... Drosophila Mushroom Body, PMCID PMC10616905);
each KC->MBON compartment therefore carries its own rate and bounds. This rule
changes functional efficacy only; structural counts are untouched. Parameters
are calibration inputs, not measured per-compartment constants.
"""
import numpy as np


class CompartmentPlasticity:
    """Efficacy update dE/dt = rate_c * eligibility * dopamine_gate_c within bounds."""

    def __init__(self, n_synapses, compartment_of_synapse, rate_per_ms_per_nm, bounds, evidence,
                 eligibility_tau_ms):
        compartment = np.asarray(compartment_of_synapse, dtype=np.int64)
        rate = np.asarray(rate_per_ms_per_nm, dtype=float)
        if compartment.shape != (n_synapses,) or rate.ndim != 1 or not len(rate):
            raise ValueError('Per-synapse compartment and per-compartment rates required')
        if not np.isfinite(eligibility_tau_ms) or eligibility_tau_ms <= 0:
            raise ValueError('Positive eligibility time constant required')
        lo = np.asarray([b[0] for b in bounds], dtype=float)
        hi = np.asarray([b[1] for b in bounds], dtype=float)
        if lo.shape != rate.shape or hi.shape != rate.shape or not np.isfinite(rate).all() \
                or np.any(rate < 0) or not np.isfinite(lo).all() or not np.isfinite(hi).all() \
                or np.any(lo <= 0) or np.any(hi <= lo):
            raise ValueError('Nonnegative rates and 0 < lower < upper per compartment required')
        if not evidence:
            raise ValueError('Evidence statement required')
        self.compartment = compartment
        self.rate, self.lower, self.upper = rate, lo, hi
        self.evidence, self.eligibility_tau_ms = str(evidence), float(eligibility_tau_ms)
        self.eligibility = np.zeros(n_synapses)

    def step(self, efficacy, kc_release, mbon_activity, dopamine_nm, dt_ms):
        w = np.asarray(efficacy, dtype=float)
        pre = np.asarray(kc_release, dtype=float)
        post = np.asarray(mbon_activity, dtype=float)
        if pre.shape != w.shape or post.shape != w.shape or not np.isfinite(w).all() \
                or np.any(w <= 0) or not np.isfinite([dopamine_nm, dt_ms]).all() or dopamine_nm < 0 or dt_ms <= 0:
            raise ValueError('Aligned positive efficacies, activities, dopamine nM and positive dt required')
        gated_rate = self.rate[self.compartment]*min(dopamine_nm, 1e6)
        self.eligibility += -np.expm1(-dt_ms/self.eligibility_tau_ms)*(pre*post-self.eligibility)
        updated = np.clip(w+gated_rate*self.eligibility*dt_ms, self.lower[self.compartment], self.upper[self.compartment])
        return updated
