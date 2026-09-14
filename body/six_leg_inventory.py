"""Per-leg capability inventory of the pinned body model. No synthetic legs.

The roadmap's six-leg expansion needs per-leg joints, muscles and actuators.
This audit reports exactly what the upstream model provides per leg and refuses
to pretend missing legs exist. Middle/hind legs and right-front muscles require
new anatomical/mesh data, not configuration.
"""
import hashlib
import json
from pathlib import Path

import numpy as np
import mujoco as mj
from flygym.compose import build_musculoskeletal_simulation

LEG_PREFIXES = ('LF', 'RF', 'LM', 'RM', 'LH', 'RH')


def inventory():
    sim, fly = build_musculoskeletal_simulation()
    model = sim.mj_model
    legs = {}
    for prefix in LEG_PREFIXES:
        joints = [mj.mj_id2name(model, mj.mjtObj.mjOBJ_JOINT, i) for i in range(model.njnt)
                  if (mj.mj_id2name(model, mj.mjtObj.mjOBJ_JOINT, i) or '').startswith('joint_'+prefix)]
        muscles = [mj.mj_id2name(model, mj.mjtObj.mjOBJ_ACTUATOR, i) for i in range(model.nu)
                   if (mj.mj_id2name(model, mj.mjtObj.mjOBJ_ACTUATOR, i) or '').startswith(prefix)]
        muscle_actuated = bool(muscles)
        legs[prefix] = {'joints': joints, 'muscles': muscles, 'muscle_actuated': muscle_actuated,
                        'position_actuated': False,
                        'status': 'muscle_actuated' if muscle_actuated else
                                  'joints_passive_only' if joints else 'absent_from_model'}
    return legs


def run():
    legs = inventory()
    complete = all(legs[p]['muscle_actuated'] for p in LEG_PREFIXES)
    report = {'scope': 'per-leg capability audit of the pinned FlyGym 2.1.0 musculoskeletal model',
        'legs': legs, 'six_leg_muscle_actuation_available': complete,
        'blocking': ['Middle and hind legs have no meshes/joints in the upstream model',
                     'Right-front leg has joints but no muscle actuators',
                     'A six-leg neuromuscular closed loop requires new anatomical data, '
                     'not a software change on this model'],
        'upstream_audit_2026_09_14': 'FlyMimic repository (gizemozd/FlyMimic) and the Oezdil et al. '
            'supplement confirm: mid/hind-leg MTU reconstructions (7 and 8) exist only as supplement '
            'figures in OpenSim, never released as model files; the referenced OpenSim pipeline repo '
            '(gizemozd/neuromechfly-muscles) is a dead 404 link; only geometry STLs for all six legs '
            'are public, with no muscle attachments outside the left front leg. The upstream gap is '
            'final unless the authors release the models.',
        'biological_acceptance': False,
        'note': 'Left-front leg remains the only muscle-actuated limb; expansion status is upstream-bound.',
        'executed_source_sha256': {'body/six_leg_inventory.py':
            hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}}
    Path('validation/six-leg-inventory.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps({p: legs[p]['status'] for p in LEG_PREFIXES}, indent=2))
    return report


if __name__ == '__main__':
    run()
