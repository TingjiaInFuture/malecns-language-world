"""Explicit observation filter and group-disjoint experiment split validation."""
import numpy as np


class Indicator:
    def __init__(self, shape, tau_ms, gain, noise_sd, seed):
        if not all(np.isfinite(v) for v in [tau_ms,gain,noise_sd]) or tau_ms <= 0 or noise_sd < 0:
            raise ValueError('Invalid measurement parameters')
        self.state = np.zeros(shape)
        self.tau,self.gain,self.noise = tau_ms,gain,noise_sd
        self.rng = np.random.default_rng(seed)

    def observe(self, activity, dt_ms):
        a = np.asarray(activity,dtype=float)
        if a.shape != self.state.shape or not np.isfinite(a).all() or not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('Invalid measurement input')
        self.state += -np.expm1(-dt_ms/self.tau)*(self.gain*a-self.state)
        return self.state+self.rng.normal(0,self.noise,self.state.shape)


def assert_disjoint_groups(records, keys=('animal_id','trajectory_id')):
    seen = {key:{} for key in keys}
    for record in records:
        split = record['split']
        if split not in ('train','validation','test'):
            raise ValueError('Unknown experimental split')
        for key in keys:
            value = record[key]
            if value is None or value == '':
                raise ValueError('Missing experimental group')
            previous = seen[key].setdefault(value,split)
            if previous != split:
                raise ValueError('Experiment leakage: '+key)
