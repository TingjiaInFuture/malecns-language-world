"""Male-specific body calibration from measured masses. Units: mg, mm, uN.

The pinned FlyGym musculoskeletal model is not male-calibrated. This module
turns an explicitly sourced male mass measurement into a uniform mass scaling
factor with a receipt, or refuses to run. It never edits the upstream XML in
place; callers apply the factor to their own derived model copy.
"""
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class MassMeasurement:
    sex: str
    strain: str
    age_days: float
    body_mass_mg: float
    source: str

    def __post_init__(self):
        if self.sex != 'male':
            raise ValueError('This calibration requires a male measurement')
        if not all(isinstance(x, str) and x for x in [self.sex, self.strain, self.source]):
            raise ValueError('Strain and citation required')
        if not np.isfinite([self.age_days, self.body_mass_mg]).all() or self.age_days <= 0 or self.body_mass_mg <= 0:
            raise ValueError('Positive age and body mass required')


def model_total_mass(model):
    """Raw sum of body_mass; MuJoCo inherits the model's mass unit (mg here)."""
    if not np.isfinite(model.body_mass).all() or np.any(model.body_mass < 0):
        raise ValueError('Invalid body masses in model')
    return float(np.sum(model.body_mass))


def calibration_factor(model, measurement, model_unit):
    if model_unit not in ('mg', 'g', 'kg'):
        raise ValueError("Declare the model's mass unit explicitly")
    total = model_total_mass(model)
    scale = {'mg': 1., 'g': 1e-3, 'kg': 1e-6}[model_unit]
    target = measurement.body_mass_mg*scale
    if total <= 0:
        raise ValueError('Model carries no mass to calibrate')
    factor = target/total
    receipt = {'measurement': {'sex': measurement.sex, 'strain': measurement.strain,
                'age_days': measurement.age_days, 'body_mass_mg': measurement.body_mass_mg,
                'source': measurement.source},
               'model_total_mass_raw': total, 'model_mass_unit': model_unit,
               'model_total_mass_mg': total/scale,
               'uniform_scale_factor': factor,
               'scope': 'uniform mass scaling only; geometry/inertia/muscle force calibration is separate',
               'biological_acceptance': False}
    receipt['sha256'] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode()).hexdigest()
    return factor, receipt


def apply_uniform_mass_scale(xml_path, factor, out_path):
    """Copy the MJCF and scale every body mass attribute; provenance stays external."""
    if not np.isfinite(factor) or factor <= 0:
        raise ValueError('Positive scale factor required')
    text = Path(xml_path).read_text(encoding='utf-8')
    changed = []
    def scale(match):
        value = float(match.group(2))*factor
        changed.append(match.group(1))
        return f'mass="{value}"'
    out = re.sub(r'(mass)="([0-9.eE+-]+)"', scale, text)
    if not changed:
        raise ValueError('No mass attributes found; unexpected model file')
    out_path = Path(out_path)
    if out_path.exists():
        raise ValueError('Refusing to overwrite an existing calibrated model')
    out_path.write_text(out, encoding='utf-8')
    return {'scaled_bodies': len(changed), 'factor': factor, 'out': str(out_path)}
