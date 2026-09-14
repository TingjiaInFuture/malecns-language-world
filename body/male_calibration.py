"""Male-specific body calibration from measured masses. Units: mg, mm, uN.

The pinned FlyGym musculoskeletal model is not male-calibrated. This module
turns an explicitly sourced male mass measurement into a uniform mass scaling
factor with a receipt, or refuses to run. It never edits the upstream XML in
place; callers apply the factor to their own derived model copy.
Run (in .venv-body): python -m body.male_calibration
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


def run():
    """Regenerate validation/male-mass-calibration.json against the pinned body model.

    Run inside .venv-body: python -m body.male_calibration
    """
    import json
    from flygym.compose import build_musculoskeletal_simulation
    from importlib.metadata import version
    male = MassMeasurement('male', 'Canton-S', 2., 0.81,
                           'Zumstein et al. 2004, J Exp Biol 207:3515-3522 (doi:10.1242/jeb.01181); '
                           'male 0.81+-0.03 mg, 2 d, 25 C')
    sim, _ = build_musculoskeletal_simulation()
    factor, receipt = calibration_factor(sim.mj_model, male, 'g')
    receipt['finding'] = (
        'FlyMimic model total mass is %.3f mg in its gram/mm/uN unit system, i.e. %.1fx the '
        'measured 1.13+-0.03 mg female and %.1fx the 0.81 mg male (Zumstein 2004). The upstream '
        'body is not mass-calibrated to either sex; any force/statement normalized to model '
        'weight inherits this bias until recalibrated.'
        % (receipt['model_total_mass_mg'], receipt['model_total_mass_mg']/1.13,
           receipt['model_total_mass_mg']/0.81))
    receipt['comparison'] = {'measured_female_mg': 1.13, 'measured_male_mg': 0.81,
                             'model_mg': receipt['model_total_mass_mg']}
    receipt['flygym_version'] = version('flygym')
    receipt['executed_source_sha256'] = {'body/male_calibration.py':
        hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    Path('validation/male-mass-calibration.json').write_text(json.dumps(receipt, indent=2),
                                                             encoding='utf-8')
    print(json.dumps({'model_mg': receipt['model_total_mass_mg'],
                      'male_factor': receipt['uniform_scale_factor']}))


if __name__ == '__main__':
    run()
