"""Passive multicompartment cable reference for circuits that need it. Units: ms, mV, pF, nS, pA.

C_m dV_k/dt = -gL_k(V_k-EL_k) + sum_neighbors ga_km (V_m-V_k) + I_syn,k + I_inj,k
Trees are defined by a parent array; root has no parent. Synaptic conductance and
reversal are supplied per step. Reserved for key circuits where dendritic/axonal
attenuation changes predictions; not a whole-brain representation.
"""
import copy
import hashlib
import json
import numpy as np
from scipy.sparse import csc_matrix
from scipy.sparse.linalg import factorized


class CableTree:
    def __init__(self, parent, capacitance_pf, leak_ns, resting_mv, axial_ns, dt_ms=.1):
        parent = np.asarray(parent, dtype=np.int64)
        n = len(parent)
        if n < 1 or parent.shape != (n,) or np.any(parent < -1) or np.any(parent >= n):
            raise ValueError('Parent array must reference earlier compartments or -1')
        for k in range(n):
            if parent[k] >= k:
                raise ValueError('Parent must precede child for a forest rooted at 0')
        arrays = [np.asarray(a, dtype=float) for a in [capacitance_pf, leak_ns, resting_mv, axial_ns]]
        if any(a.shape not in [(), (n,)] or not np.isfinite(a).all() for a in arrays):
            raise ValueError('Finite scalar or per-compartment parameters required')
        if np.any(arrays[0] <= 0) or np.any(arrays[1] <= 0) or np.any(np.broadcast_to(arrays[3], (n,)) < 0):
            raise ValueError('Positive membrane parameters and nonnegative axial conductance required')
        if not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('Positive time step required')
        self.n = n
        self.parent = parent
        self.capacitance = np.broadcast_to(arrays[0], (n,)).astype(float).copy()
        self.leak = np.broadcast_to(arrays[1], (n,)).astype(float).copy()
        self.resting = np.broadcast_to(arrays[2], (n,)).astype(float).copy()
        self.axial = np.broadcast_to(arrays[3], (n,)).astype(float).copy()
        self.dt_ms = float(dt_ms)
        self.v = self.resting.copy()
        # Backward-Euler system: (C/dt + L + sum ga) V_new = (C/dt) V_old + L*EL + I  per compartment.
        rows, cols, data = [], [], []
        diagonal = self.capacitance/self.dt_ms+self.leak
        for k in range(n):
            p = int(parent[k])
            if p >= 0:
                g = self.axial[k]
                diagonal[k] += g
                diagonal[p] += g
        for k in range(n):
            rows.append(k); cols.append(k); data.append(diagonal[k])
        for k in range(n):
            p = int(parent[k])
            if p >= 0:
                g = self.axial[k]
                rows.extend([k, p]); cols.extend([p, k]); data.extend([-g, -g])
        matrix = csc_matrix((data, (rows, cols)), shape=(n, n))
        self._solve = factorized(matrix)
        self._diagonal = diagonal
        self.ticks = 0
        self.fingerprint = hashlib.sha256(json.dumps({'n': n, 'parent': parent.tolist(), 'dt_ms': dt_ms,
            'capacitance_pf': self.capacitance.tolist(), 'leak_ns': self.leak.tolist(),
            'resting_mv': self.resting.tolist(), 'axial_ns': self.axial.tolist()}, sort_keys=True).encode()).hexdigest()

    def step(self, current_pa, synaptic_ns=None, reversal_mv=None):
        current = np.asarray(current_pa, dtype=float)
        if current.shape != (self.n,) or not np.isfinite(current).all():
            raise ValueError('Per-compartment injected current required in pA')
        drive = self.capacitance/self.dt_ms*self.v+self.leak*self.resting+current
        if synaptic_ns is not None or reversal_mv is not None:
            if synaptic_ns is None or reversal_mv is None:
                raise ValueError('Synaptic conductance and reversal must be supplied together')
            g = np.asarray(synaptic_ns, dtype=float)
            e = np.asarray(reversal_mv, dtype=float)
            if g.shape != (self.n,) or e.shape != (self.n,) or not np.isfinite(g).all() \
                    or not np.isfinite(e).all() or np.any(g < 0):
                raise ValueError('Finite nonnegative synaptic conductance with reversal required')
            drive = drive+g*e
            # The matrix must include g on the diagonal for this step only.
            from scipy.sparse import csc_matrix as _csc
            from scipy.sparse.linalg import spsolve as _spsolve
            rows, cols, data = [], [], []
            diagonal = self._diagonal+g
            for k in range(self.n):
                rows.append(k); cols.append(k); data.append(diagonal[k])
            for k in range(self.n):
                p = int(self.parent[k])
                if p >= 0:
                    rows.extend([k, p]); cols.extend([p, k]); data.extend([-self.axial[k], -self.axial[k]])
            v_new = _spsolve(_csc((data, (rows, cols)), shape=(self.n, self.n)), drive)
        else:
            v_new = self._solve(drive)
        if not np.isfinite(v_new).all():
            raise FloatingPointError('Nonfinite cable voltage')
        self.v, self.ticks = v_new, self.ticks+1
        return self.v.copy()

    def snapshot(self):
        return copy.deepcopy({'fingerprint': self.fingerprint, 'ticks': self.ticks, 'v': self.v})

    def restore(self, state):
        if state.get('fingerprint') != self.fingerprint:
            raise ValueError('Checkpoint morphology, parameters or clock differ')
        v = np.asarray(state['v'], dtype=float)
        if v.shape != (self.n,) or not np.isfinite(v).all():
            raise ValueError('Invalid checkpoint voltages')
        if not isinstance(state['ticks'], int) or state['ticks'] < 0:
            raise ValueError('Invalid clock')
        self.v, self.ticks = v.copy(), state['ticks']


def sealed_end_attenuation(n, length_constant_compartments):
    """Analytic DC attenuation of a uniform sealed cable driven at the root."""
    l = float(length_constant_compartments)
    if n < 1 or not np.isfinite(l) or l <= 0:
        raise ValueError('Positive electrotonic length required')
    positions = np.arange(n)/l
    total = (n-1)/l
    return np.cosh(total-positions)/np.cosh(total)
