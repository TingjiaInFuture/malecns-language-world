"""Conservative nutrient/water bookkeeping, with no action-selection outputs.

Parameters and units must be calibrated externally; output is internal state.
"""
from dataclasses import dataclass
import math


@dataclass
class Homeostasis:
    crop_ug: float = 0.
    nutrient_ug: float = 0.
    water_ug: float = 0.

    def step(self, dt_s, contact, ingestion_ug_s, drinking_ug_s, absorption_tau_s,
             consumption_ug_s, water_loss_ug_s):
        values = [dt_s,ingestion_ug_s,drinking_ug_s,absorption_tau_s,consumption_ug_s,water_loss_ug_s,
                  self.crop_ug,self.nutrient_ug,self.water_ug]
        if not all(math.isfinite(v) and v >= 0 for v in values) or absorption_tau_s <= 0:
            raise ValueError('Nonnegative physical rates and positive absorption time required')
        intake = ingestion_ug_s*dt_s if contact else 0.
        drink = drinking_ug_s*dt_s if contact else 0.
        self.crop_ug += intake
        absorbed = self.crop_ug*(-math.expm1(-dt_s/absorption_tau_s))
        self.crop_ug -= absorbed
        used = min(self.nutrient_ug+absorbed,consumption_ug_s*dt_s)
        self.nutrient_ug += absorbed-used
        lost = min(self.water_ug+drink,water_loss_ug_s*dt_s)
        self.water_ug += drink-lost
        return {'ingested_ug':intake,'absorbed_ug':absorbed,'consumed_ug':used,
                'drunk_ug':drink,'water_lost_ug':lost}
