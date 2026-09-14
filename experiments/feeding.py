"""Feeding internal-state experiment: contact, ingestion, absorption, satiation.

The proboscis is not modeled geometrically; contact events are explicit inputs
with schedule provenance. No foraging behavior, no food-seeking planner, no
remote sensing. Output is internal state only, per the roadmap constraint that
hunger changes circuit gain rather than calling an external planner.
"""
from dataclasses import dataclass

import numpy as np

from physiology.homeostasis import Homeostasis
from world.nutrients import SubstratePatch


@dataclass(frozen=True)
class ContactSchedule:
    """Contact intervals in seconds with an explicit provenance string."""
    starts_s: tuple
    durations_s: tuple
    provenance: str

    def __post_init__(self):
        if len(self.starts_s) != len(self.durations_s) or not self.provenance:
            raise ValueError('Aligned contact intervals with provenance required')
        for start, duration in zip(self.starts_s, self.durations_s):
            if not np.isfinite([start, duration]).all() or start < 0 or duration <= 0:
                raise ValueError('Nonnegative start and positive duration required')
        ends = np.asarray(self.starts_s)+np.asarray(self.durations_s)
        if len(self.starts_s) > 1 and np.any(np.asarray(self.starts_s)[1:] < ends[:-1]):
            raise ValueError('Contact intervals must not overlap')


def run(patch, schedule, dt_s, ingestion_rate_ug_s, drinking_rate_ug_s,
        absorption_tau_s, consumption_ug_s, water_loss_ug_s, total_s):
    homeostasis = Homeostasis()
    contact = np.zeros(total_s)
    for start, duration in zip(schedule.starts_s, schedule.durations_s):
        lo, hi = int(round(start)), int(round(start+duration))
        contact[lo:hi] = 1.
    samples = []
    for tick in range(total_s):
        flows = homeostasis.step(dt_s, bool(contact[tick]), ingestion_rate_ug_s, drinking_rate_ug_s,
                                 absorption_tau_s, consumption_ug_s, water_loss_ug_s)
        if contact[tick]:
            patch.ingest(True, ingestion_rate_ug_s*dt_s)
        samples.append({'t_s': tick*dt_s, 'contact': float(contact[tick]),
                        'crop_ug': homeostasis.crop_ug, 'nutrient_ug': homeostasis.nutrient_ug,
                        'water_ug': homeostasis.water_ug, **flows})
    return {'scope': 'internal feeding state under an explicit contact schedule; no behavior claim',
            'schedule_provenance': schedule.provenance, 'biological_acceptance': False, 'samples': samples}
