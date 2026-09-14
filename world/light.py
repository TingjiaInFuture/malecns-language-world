"""Photon-flux light field. SI units: W/m^2, photons/(m^2 s) at receptor points.

No single 'light' scalar: each query returns spectral-band photon rate at a
retinal point so retinotopy must be supplied by the caller. Phototransduction
gain is not modeled here.
"""
import numpy as np

# Planck constant times speed of light, J*m.
HC = 1.98644586e-25


def photon_rate_per_m2(irradiance_w_m2, wavelength_m):
    irradiance = np.asarray(irradiance_w_m2, dtype=float)
    wavelength = np.asarray(wavelength_m, dtype=float)
    if not np.isfinite(irradiance).all() or np.any(irradiance < 0):
        raise ValueError('Nonnegative spectral irradiance required')
    if wavelength.shape != irradiance.shape or not np.isfinite(wavelength).all() or np.any(wavelength <= 0):
        raise ValueError('Positive wavelength per band required')
    return irradiance/(HC/wavelength)


def retinal_sample(photon_rate, acceptance_sr, area_m2):
    """Photons/s reaching one photoreceptor given optical acceptance and area."""
    rate = np.asarray(photon_rate, dtype=float)
    if not np.isfinite(rate).all() or np.any(rate < 0) or not np.isfinite([acceptance_sr, area_m2]).all() \
            or acceptance_sr <= 0 or area_m2 <= 0:
        raise ValueError('Nonnegative rate, positive acceptance solid angle and receptor area required')
    return rate*acceptance_sr*area_m2


def day_night_irradiance(solar_elevation_deg, clear_sky_w_m2=1000.):
    """Engineering sky model: direct+diffuse irradiance vs sun elevation."""
    if not np.isfinite([solar_elevation_deg, clear_sky_w_m2]).all() or clear_sky_w_m2 < 0 \
            or solar_elevation_deg < -90 or solar_elevation_deg > 90:
        raise ValueError('Elevation in [-90,90] deg and nonnegative sky scale required')
    if solar_elevation_deg <= 0:
        return 0.
    return float(clear_sky_w_m2*np.sin(np.radians(solar_elevation_deg)))
