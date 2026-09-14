"""Explicit unit conversions for interface data. No silent scaling.

Every conversion names its factor and direction; model-unit quantities (MuJoCo
g/mm/uN system) are never mixed into SI paths implicitly.
"""
import numpy as np

DEG_PER_RAD = 180./np.pi


def deg_to_rad(angle_deg):
    values = np.asarray(angle_deg, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Finite angles required')
    return values/DEG_PER_RAD


def rad_to_deg(angle_rad):
    values = np.asarray(angle_rad, dtype=float)
    if not np.isfinite(values).all():
        raise ValueError('Finite angles required')
    return values*DEG_PER_RAD


def voltage_to_current_pa(voltage_mv, conductance_ns):
    """Ohm's law with mV and nS: 1 mV * 1 nS = 1 pA."""
    v = np.asarray(voltage_mv, dtype=float)
    g = np.asarray(conductance_ns, dtype=float)
    if not np.isfinite(v).all() or not np.isfinite(g).all() or np.any(g < 0):
        raise ValueError('Finite voltages and nonnegative conductances required')
    return v*g


def model_force_to_un(force_model, model_system='g_mm_s'):
    """Convert FlyMimic-model force to uN. In g/mm/s, 1 g*mm/s^2 = 1e-6 N = 1 uN."""
    values = np.asarray(force_model, dtype=float)
    if model_system != 'g_mm_s':
        raise ValueError('Only the pinned g/mm/s model system is declared')
    if not np.isfinite(values).all():
        raise ValueError('Finite forces required')
    return values


def spike_rate_hz(spike_count, duration_s):
    if not np.isfinite(spike_count) or spike_count < 0 or not np.isfinite(duration_s) or duration_s <= 0:
        raise ValueError('Nonnegative count and positive duration required')
    return float(spike_count)/float(duration_s)
