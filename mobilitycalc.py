import numpy as np
import scipy


def calc_charged_frac(charge, d_nm):
    """Wiedensohler 1988, returns charged fraction"""
    a_coeff = {
        -2: [-26.3328, 35.9044, -21.4608, 7.0867, -1.3088, 0.1051],
        -1: [-2.3197, 0.6175, 0.6201, -0.1105, -0.1260, 0.0297],
        0: [-0.0003, -0.1014, 0.3073, -0.3372, 0.1023, -0.0105],
        1: [-2.3484, 0.6044, 0.4800, 0.0013, -0.1553, 0.0320],
        2: [-44.4756, 79.3772, -62.8900, 26.4492, -5.7480, 0.5049],
    }
    power_sum = []
    for i in range(6):
        power_sum.append((a_coeff[charge][i] * np.log10(d_nm) ** i))
    charged_frac = 10 ** sum(power_sum)
    return charged_frac


def calc_slip_correction(d_nm):
    """Seinfeld and Pandis 2016 (9.34), returns C_c"""
    mean_free_path = 65.1  # nm
    slip_correction = 1 + 2 * mean_free_path / d_nm * (
        1.257 + 0.4 * np.exp((-1.1 * d_nm) / (2 * mean_free_path))
    )
    return slip_correction


def calc_diffusion_coeff(d_nm):
    """Seinfeld and Pandis (9.73), returns D = [m^2/s]"""
    k = 1.381e-23  # J/K [Boltzman Constant]
    t = 273  # K [Temperature]
    c_c = calc_slip_correction(d_nm)  # 1 [Slip Correction]
    mu = 1.72e-05  # kg/(m*s) [Dynamic Viscosity]
    d_p = d_nm * 1e-9  # m
    diffusion_coeff = (k * t * c_c) / (3 * np.pi * mu * d_p)
    return diffusion_coeff


def calc_deposition_param(d_nm, l_eff_m, q_sample_sccm):
    """Jiang 2011 (Eqn. 8), returns mu"""
    d = calc_diffusion_coeff(d_nm)  # m^2/s [Diffusion coefficient]
    q_cm_s = q_sample_sccm / 60  # cm^3/s
    q_m_s = q_cm_s * 1e-6  # m^3/s
    deposition_param = (np.pi * d * l_eff_m) / q_m_s
    return deposition_param


def calc_dma_penetration(d_nm, l_eff_m, q_sample_sccm):
    """Jiang 2011 (Eqn. 9 & 10), returns dma penetration efficiency"""
    mu = calc_deposition_param(d_nm, l_eff_m, q_sample_sccm)  # 1 [Deposition Parameter]
    if mu > 0.02:
        penetration_eff = (
            0.819 * np.exp(-3.66 * mu)
            + 0.0975 * np.exp(-22.3 * mu)
            + 0.0325 * np.exp(-57.0 * mu)
            + 0.0154 * np.exp(-107.6 * mu)
        )
    else:
        penetration_eff = 1.0 - 2.56 * mu ** (2 / 3) + 1.2 * mu + 0.1767 * mu ** (4 / 3)
    return penetration_eff


def calc_mobility_from_voltage(volt, q_sheath_ccm, q_excess_ccm, dma_l_cm, dma_od_cm, dma_id_cm):
    """Stolzenburg 2008 (Eqn. 1 & 3), returns electrical mobility cm^2/(V*s)"""
    q_sheath = q_sheath_ccm / 60  # cm^3/s
    q_excess = q_excess_ccm / 60  # cm^3/s
    elec_mobility = (
        (q_sheath + q_excess) / (4 * np.pi * volt * dma_l_cm) * np.log(dma_od_cm / dma_id_cm)
    )
    return elec_mobility


def calc_voltage_from_mobility(
    mobil_cm, q_sheath_ccm, q_excess_ccm, dma_l_cm, dma_od_cm, dma_id_cm
):
    """Stolzenburg 2008 (Eqn. 1 & 3), returns electrical mobility cm^2/(V*s)"""
    q_sheath = q_sheath_ccm / 60  # cm^3/s
    q_excess = q_excess_ccm / 60  # cm^3/s
    volt = (q_sheath + q_excess) / (4 * np.pi * mobil_cm * dma_l_cm) * np.log(dma_od_cm / dma_id_cm)
    return volt


def calc_mobility_from_dia(d_nm):
    """Seinfeld and Pandis 2016 (9.50), returns electrical mobility cm^2/(V*s)"""
    q = 1.60e-19  # C [1 elementary charge]
    mu = 1.72e-05  # kg/(m*s) [Dynamic Viscosity]
    c_c = calc_slip_correction(d_nm)  # 1 [Slip Correction]
    elec_mobility = (q * c_c) / (3 * np.pi * mu * d_nm * 1e-9)
    elec_mobility_cm = elec_mobility * 1e4
    return elec_mobility_cm


def calc_dia_from_mobility(elec_mobility_cm, d_set):
    def calc_mobility_from_dia1(d_nm):
        """Seinfeld and Pandis 2016 (9.50), returns electrical mobility cm^2/(V*s)"""
        q = 1.60217663e-19  # C [1 elementary charge]
        mu = 1.72e-05  # kg/(m*s) [Dynamic Viscosity]
        mean_free_path = 65.1  # nm
        return (
            elec_mobility_cm
            - (
                q
                * (
                    1
                    + 2
                    * mean_free_path
                    / d_nm
                    * (1.257 + 0.4 * np.exp((-1.1 * d_nm) / (2 * mean_free_path)))
                )
            )
            / (3 * np.pi * mu * d_nm * 1e-9)
            * 1e4
        )

    sol = scipy.optimize.fsolve(calc_mobility_from_dia1, d_set)
    return sol[0]


def calc_dia_from_voltage(volt, q_sheath_ccm, q_excess_ccm, dma_l_cm, dma_od_cm, dma_id_cm, d_set):
    elec_mobility_cm = calc_mobility_from_voltage(
        volt, q_sheath_ccm, q_excess_ccm, dma_l_cm, dma_od_cm, dma_id_cm
    )
    d_nm = calc_dia_from_mobility(elec_mobility_cm, d_set)
    return d_nm
