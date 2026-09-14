"""Ingestible substrate patches; µg quantities, SI concentrations.

Feeding requires mouthpart contact with a substrate patch; no remote detection,
no planner. Absorption and satiation live in physiology.homeostasis.
"""
import numpy as np


class SubstratePatch:
    def __init__(self, sugar_mol_m3, water_fraction, mass_ug):
        if not np.isfinite([sugar_mol_m3, water_fraction, mass_ug]).all() \
                or sugar_mol_m3 < 0 or not 0 <= water_fraction <= 1 or mass_ug < 0:
            raise ValueError('Nonnegative sugar, water fraction in [0,1] and mass required')
        self.sugar_mol_m3 = float(sugar_mol_m3)
        self.water_fraction = float(water_fraction)
        self.mass_ug = float(mass_ug)

    def ingest(self, contact, requested_ug):
        """Remove and return consumed mass; contact is a physical mouthpart event."""
        if not np.isfinite(requested_ug) or requested_ug < 0:
            raise ValueError('Nonnegative requested mass required')
        taken = min(requested_ug, self.mass_ug) if contact else 0.
        self.mass_ug -= taken
        return {'ingested_ug': taken, 'sugar_mol_m3': self.sugar_mol_m3,
                'water_fraction': self.water_fraction}
