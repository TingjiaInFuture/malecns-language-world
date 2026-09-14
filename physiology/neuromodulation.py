"""Modulator pools with explicit receptor maps; no structure-free global gain.

A modulator changes physiology only through a reviewed receptor mapping that
names targets, effect bounds and evidence. Pools carry concentration in nM with
first-order clearance. Without a mapping, release changes concentration and
nothing else. Default constants are engineering fixtures, not measured titers.
"""
import numpy as np


class ModulatorPool:
    def __init__(self, name, clearance_tau_s, baseline_nm=0., ceiling_nm=np.inf):
        if not name or not np.isfinite(clearance_tau_s) or clearance_tau_s <= 0 \
                or not np.isfinite(baseline_nm) or baseline_nm < 0:
            raise ValueError('Named pool with positive clearance and nonnegative baseline required')
        if ceiling_nm < baseline_nm:
            raise ValueError('Ceiling below baseline')
        self.name = str(name)
        self.clearance_tau_s = float(clearance_tau_s)
        self.baseline_nm = float(baseline_nm)
        self.ceiling_nm = float(ceiling_nm)
        self.concentration_nm = float(baseline_nm)

    def release(self, amount_nm):
        if not np.isfinite(amount_nm) or amount_nm < 0:
            raise ValueError('Nonnegative release required')
        self.concentration_nm = min(self.concentration_nm+amount_nm, self.ceiling_nm)

    def step(self, dt_s):
        if not np.isfinite(dt_s) or dt_s <= 0:
            raise ValueError('Positive time step required')
        decay = self.concentration_nm-self.baseline_nm
        self.concentration_nm = self.baseline_nm+decay*np.exp(-dt_s/self.clearance_tau_s)
        return self.concentration_nm


class ReceptorMap:
    """Multiplicative gain modulation confined to reviewed targets and bounds."""

    def __init__(self, entries):
        self.entries = []
        seen = set()
        keys = ('modulator', 'receptor', 'targets', 'lower', 'upper', 'evidence')
        for e in entries:
            if set(e) != set(keys) or not e['evidence'] or not e['modulator'] or not e['receptor']:
                raise ValueError('Each mapping needs modulator, receptor, targets, bounds, evidence')
            targets = np.asarray(e['targets'])
            if targets.ndim != 1 or not len(targets) or not np.isfinite([e['lower'], e['upper']]).all() \
                    or not 0 <= e['lower'] < e['upper']:
                raise ValueError('Nonempty target vector and 0 <= lower < upper required')
            key = (e['modulator'], e['receptor'])
            if key in seen:
                raise ValueError('Duplicate receptor mapping ' + str(key))
            seen.add(key)
            self.entries.append({'modulator': e['modulator'], 'receptor': e['receptor'],
                'targets': targets.astype(np.int64), 'lower': float(e['lower']),
                'upper': float(e['upper']), 'evidence': str(e['evidence'])})

    def gain(self, modulator, concentration_nm, km_nm, size):
        """Per-neuron multiplicative factors from saturating dose-response c/(c+Km).

        Zero concentration means no effect (factor 1); saturation drives the
        factor to the enhancing bound when upper>1, otherwise to the suppressive
        bound. Unmapped neurons keep factor 1.
        """
        if not np.isfinite([concentration_nm, km_nm]).all() or concentration_nm < 0 or km_nm <= 0:
            raise ValueError('Nonnegative concentration and positive Km required')
        if not isinstance(size, int) or size < 1:
            raise ValueError('Neuron count required')
        factors = np.ones(size)
        response = concentration_nm/(concentration_nm+km_nm)
        touched = np.zeros(size, dtype=bool)
        for e in self.entries:
            if e['modulator'] != modulator:
                continue
            idx = e['targets']
            if np.any(idx < 0) or np.any(idx >= size):
                raise ValueError('Receptor target outside neuron set')
            target = e['upper'] if e['upper'] > 1. else e['lower']
            factors[idx] *= 1.+(target-1.)*response
            touched[idx] |= response > 0.
        return factors, touched
