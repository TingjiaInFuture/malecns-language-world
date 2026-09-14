"""Motor-unit recruitment with the size principle. Units: mV, Hz, uN, ms.

Each unit carries an explicit recruitment threshold and force-per-spike with an
evidence string; nothing defaults to invented physiology. Order is threshold
order, never cell-name order. This models motor-unit force summation for
prediction tests; MuJoCo Hill muscles remain the body-side actuator.
"""
from dataclasses import dataclass
import numpy as np


@dataclass(frozen=True)
class MotorUnit:
    neuron_id: int
    muscle: str
    threshold_hz: float
    force_per_spike_un: float
    relaxation_tau_ms: float
    evidence: str

    def __post_init__(self):
        values = [self.threshold_hz, self.force_per_spike_un, self.relaxation_tau_ms]
        if not all(np.isfinite(v) and v > 0 for v in values) or not self.evidence or not self.muscle:
            raise ValueError('Positive threshold, force-per-spike and relaxation with evidence required')


class MotorUnitPool:
    def __init__(self, units):
        self.units = tuple(sorted(units, key=lambda u: u.threshold_hz))
        if not self.units:
            raise ValueError('At least one motor unit required')
        self.muscles = tuple(sorted({u.muscle for u in self.units}))
        self._muscle_index = np.array([self.muscles.index(u.muscle) for u in self.units])
        self._force_state = np.zeros(len(self.units))

    def order(self):
        """Recruitment order by threshold; slow units first by definition."""
        return [u.neuron_id for u in self.units]

    def step(self, firing_rate_hz, dt_ms):
        rate = np.asarray(firing_rate_hz, dtype=float)
        if rate.shape != (len(self.units),) or not np.isfinite(rate).all() or np.any(rate < 0) \
                or not np.isfinite(dt_ms) or dt_ms <= 0:
            raise ValueError('Per-unit nonnegative firing rates and positive dt required')
        spikes = rate*dt_ms/1000.
        decay = np.exp(-dt_ms/np.array([u.relaxation_tau_ms for u in self.units]))
        self._force_state = self._force_state*decay+spikes*np.array([u.force_per_spike_un for u in self.units])
        per_muscle = {m: 0. for m in self.muscles}
        for i, muscle in enumerate(self._muscle_index):
            per_muscle[self.muscles[muscle]] += float(self._force_state[i])
        return per_muscle

    def recruited(self, drive_hz):
        """Unit-level threshold check for a common input rate."""
        drive = float(drive_hz)
        if not np.isfinite(drive) or drive < 0:
            raise ValueError('Nonnegative drive required')
        return {u.neuron_id: bool(drive >= u.threshold_hz) for u in self.units}
