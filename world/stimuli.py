"""Minimal diffusion reference and contact gating; parameters are supplied in SI."""
import numpy as np


def odor_puff_mol_m3(position_m, source_m, elapsed_s, amount_mol, diffusion_m2_s, wind_m_s):
    if not np.isfinite([elapsed_s,amount_mol,diffusion_m2_s]).all() or elapsed_s <= 0 or amount_mol < 0 or diffusion_m2_s <= 0:
        raise ValueError('Positive elapsed time and diffusivity required')
    vectors = [np.asarray(x,dtype=float) for x in [position_m,source_m,wind_m_s]]
    if any(x.shape != (3,) or not np.isfinite(x).all() for x in vectors):
        raise ValueError('Expected finite three-dimensional SI vectors')
    p,s,w = vectors
    delta = p-s-w*elapsed_s
    variance = 4*diffusion_m2_s*elapsed_s
    return float(amount_mol/(np.pi*variance)**1.5*np.exp(-delta@delta/variance))


def taste_concentration(contact, concentration_mol_m3):
    if not np.isfinite(concentration_mol_m3) or concentration_mol_m3 < 0:
        raise ValueError('Invalid solution concentration')
    return float(concentration_mol_m3) if contact else 0.


def receptor_current(concentration_mol_m3, kd_mol_m3, maximum_pa):
    if not np.isfinite([concentration_mol_m3,kd_mol_m3,maximum_pa]).all() or concentration_mol_m3 < 0 or kd_mol_m3 <= 0:
        raise ValueError('Invalid receptor parameters')
    return maximum_pa*concentration_mol_m3/(kd_mol_m3+concentration_mol_m3)
