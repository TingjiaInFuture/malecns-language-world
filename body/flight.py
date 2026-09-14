"""Flapping-flight aerodynamics scaffold. SI units: m, s, N, Hz, rad.

Quasi-steady stroke-averaged coefficients are declared hypotheses with explicit
values supplied by the caller; nothing here is validated against measured flight
forces. This exists so the flight work package has unit-correct equations, not
to claim a flying digital fly. Wing hinge, flight muscle kinetics, halter
feedback and aeroelastic effects all await their own data.
"""
import numpy as np

RHO_AIR = 1.2  # kg/m^3 at ~20 C, declared assumption


def mean_wing_chord_m(wing_length_m, aspect_ratio):
    if not np.isfinite([wing_length_m, aspect_ratio]).all() or wing_length_m <= 0 or aspect_ratio <= 0:
        raise ValueError('Positive wing length and aspect ratio required')
    return wing_length_m*2./aspect_ratio


def stroke_averaged_force_n(wing_length_m, chord_m, stroke_amplitude_rad, frequency_hz,
                            lift_coefficient, drag_coefficient):
    """Stroke-averaged lift and drag magnitudes perpendicular/along stroke plane."""
    if not np.isfinite([wing_length_m, chord_m, stroke_amplitude_rad, frequency_hz,
                        lift_coefficient, drag_coefficient]).all() or min(wing_length_m, chord_m,
                        stroke_amplitude_rad, frequency_hz) <= 0:
        raise ValueError('Positive geometry, amplitude, frequency and coefficients required')
    area_m2 = wing_length_m*chord_m*0.5  # planform approximation, declared hypothesis
    tip_speed_m_s = wing_length_m*stroke_amplitude_rad*frequency_hz*np.pi
    dynamic_pressure = 0.5*RHO_AIR*tip_speed_m_s**2
    return {'lift_n': float(dynamic_pressure*area_m2*lift_coefficient),
            'drag_n': float(dynamic_pressure*area_m2*drag_coefficient),
            'wing_tip_speed_m_s': float(tip_speed_m_s),
            'planform_area_m2': float(area_m2)}


def mechanical_power_w(force_n, tip_speed_m_s):
    if not np.isfinite([force_n, tip_speed_m_s]).all() or force_n < 0 or tip_speed_m_s < 0:
        raise ValueError('Nonnegative force and speed required')
    return float(force_n*tip_speed_m_s)
