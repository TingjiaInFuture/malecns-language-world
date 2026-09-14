"""Electrical coupling as an explicit current term. Units: mV, nS, pA.

I_i = sum_j g_ij (V_j - V_i) for reviewed pairs. No structural edge becomes an
electrical synapse without an explicit conductance and evidence. The caller adds
the returned current to its injected-current input; state stays in the core.
"""
import numpy as np


class GapJunctions:
    def __init__(self, n, pre, post, conductance_ns, evidence):
        pre = np.asarray(pre, dtype=np.int64)
        post = np.asarray(post, dtype=np.int64)
        g = np.asarray(conductance_ns, dtype=float)
        if n < 1 or pre.ndim != 1 or pre.shape != post.shape or g.shape != pre.shape:
            raise ValueError('Aligned pair and conductance arrays required')
        if np.any(pre < 0) or np.any(pre >= n) or np.any(post < 0) or np.any(post >= n) or np.any(pre == post):
            raise ValueError('Pairs must connect distinct neurons inside the set')
        if not np.isfinite(g).all() or np.any(g <= 0) or not evidence:
            raise ValueError('Positive finite conductance and evidence for every electrical synapse required')
        self.n = n
        self.pre, self.post = pre, post
        self.g = g
        self.evidence = str(evidence)

    def current_pa(self, v):
        v = np.asarray(v, dtype=float)
        if v.shape != (self.n,) or not np.isfinite(v).all():
            raise ValueError('Per-neuron voltages required')
        delta = v[self.post]-v[self.pre]
        current = np.zeros(self.n)
        np.add.at(current, self.pre, self.g*delta)
        np.add.at(current, self.post, -self.g*delta)
        return current
