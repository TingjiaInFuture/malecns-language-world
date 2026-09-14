"""Contact, temperature and humidity fields. SI units; touch is physical only.

Mechanosensory transduction is downstream; this layer reports geometry and
physical quantities, never a direction or action hint.
"""
import numpy as np


def touch_events(positions_m, surface_z_m, penetration_threshold_m):
    positions = np.asarray(positions_m, dtype=float)
    if positions.ndim != 2 or positions.shape[1] != 3 or not np.isfinite(positions).all():
        raise ValueError('Finite 3-D contact candidate positions required')
    if not np.isfinite([surface_z_m, penetration_threshold_m]).all() or penetration_threshold_m < 0:
        raise ValueError('Surface height and nonnegative threshold required')
    return positions[:, 2] <= surface_z_m+penetration_threshold_m


def thermal_environment(air_temperature_c, surface_temperature_c, relative_humidity):
    values = [air_temperature_c, surface_temperature_c, relative_humidity]
    if not np.isfinite(values).all() or not 0 <= relative_humidity <= 1:
        raise ValueError('Finite temperatures and relative humidity in [0,1] required')
    return {'air_temperature_c': float(air_temperature_c),
            'surface_temperature_c': float(surface_temperature_c),
            'relative_humidity': float(relative_humidity)}


def laminar_wind(direction_unit, speed_m_s):
    """Uniform laminar flow vector; position-independent by definition."""
    direction = np.asarray(direction_unit, dtype=float)
    if direction.shape != (3,) or not np.isfinite(direction).all() \
            or not np.isfinite(speed_m_s) or speed_m_s < 0:
        raise ValueError('Finite 3-D direction and nonnegative speed required')
    norm = float(np.linalg.norm(direction))
    if norm <= 0:
        raise ValueError('Nonzero wind direction required')
    return direction/norm*speed_m_s
