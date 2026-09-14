"""Joint-state to proprioceptor-format signals. Units: rad, rad/s, pA.

Extracts physical joint state and shapes it through declared receptor transfer
hypotheses (position/velocity/load channels). The FeCO-inspired dynamic+static
split is a hypothesis structure, not measured club/hook/claw kinetics; gains
and thresholds arrive from evidence-carrying configuration, never defaults.
"""
import numpy as np


class ProprioceptiveChannel:
    def __init__(self, joint_name, kind, gain_pa_per_unit, threshold, evidence):
        if kind not in ('position_rad', 'velocity_rad_s', 'load_model_units'):
            raise ValueError('Unknown channel kind')
        values = [gain_pa_per_unit, threshold]
        if not all(np.isfinite(v) for v in values) or not joint_name or not evidence:
            raise ValueError('Joint name, finite gain/threshold and evidence required')
        self.joint_name, self.kind = str(joint_name), kind
        self.gain_pa_per_unit, self.threshold = float(gain_pa_per_unit), float(threshold)
        self.evidence = str(evidence)

    def current_pa(self, joint_state):
        value = float(joint_state)
        if not np.isfinite(value):
            raise ValueError('Finite joint state required')
        # All channels are signed linear encodings; the threshold is the zero-current offset.
        return self.gain_pa_per_unit*(value-self.threshold)


def femoral_chordotonal_hypothesis(tibia_angle_rad, tibia_velocity_rad_s, static_gain_pa_per_rad,
                                   dynamic_gain_pa_per_rad_per_s, static_threshold_rad,
                                   dynamic_threshold_rad_s, evidence):
    """Position+velocity receptor pair in FeCO style; signs follow flexion-positive convention."""
    arrays = [np.asarray(x, dtype=float) for x in [tibia_angle_rad, tibia_velocity_rad_s]]
    parameters = [static_gain_pa_per_rad, dynamic_gain_pa_per_rad_per_s,
                  static_threshold_rad, dynamic_threshold_rad_s]
    if any(not np.isfinite(a).all() for a in arrays) or not all(np.isfinite(p) for p in parameters) or not evidence:
        raise ValueError('Finite signals/parameters and evidence required')
    static = static_gain_pa_per_rad*(arrays[0]-static_threshold_rad)
    # Dead zone: below the speed threshold the dynamic afferent stays silent.
    dynamic = dynamic_gain_pa_per_rad_per_s*np.maximum(np.abs(arrays[1])-dynamic_threshold_rad_s, 0.)*np.sign(arrays[1])
    return {'static_pa': static, 'dynamic_pa': dynamic,
            'hypothesis': 'FeCO-style static/dynamic split; club/hook kinetics pending measured afferent data'}
