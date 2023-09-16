import numpy as np
import pandas as pd


def sigmoid(x, eta, dp_50, k, a, c):
    return eta / (1 + np.exp(-k * (x - dp_50))) - np.exp(-a * x + c)


def hill_langmuir_loss(x, k_a, n, loss, q):
    return 1 / (1 + (k_a / x) ** n) - np.exp(-loss * x) + q


def mu_g(T_degC=20):
    """Returns the air viscosity [kg/m-s]"""
    T_K = T_degC + 273.15
    mu_g_r = 1.83 * 10**-5  # reference gas viscosity [kg/m-s]
    T_r = 296.15  # reference temperature [K]
    P_r = 101.3  # reference pressure [kPa]
    Suth = 110.4  # Sutherland const. [K]
    mu = mu_g_r * (T_r + Suth) / (T_K + Suth) * (T_K / T_r) ** (3 / 2)
    return mu


def lambda_mfp(T_degC=20, P_kPa=101.3):
    """Returns the gas mean free path [m]"""
    T_K = T_degC + 273.15
    lambda_mfp_r = 6.73 * 10**-8  # reference mean free path [m]
    T_r = 296.15  # reference temperature [K]
    P_r = 101.3  # reference pressure [kPa]
    Suth = 110.4  # Sutherland const. [K]

    lam = (
        lambda_mfp_r
        * (P_r / P_kPa)
        * (T_K / T_r)
        * (1 + Suth / T_r)
        / (1 + Suth / T_K)
    )
    return lam


def Kn(Dp, T_degC=20, P_kPa=101.3):
    """Returns the Knudsen number"""
    Dp = np.array([Dp]).flatten()
    Dp_SI = Dp * 1e-9
    Kn = 2 * lambda_mfp(T_degC, P_kPa) / Dp_SI

    return Kn if len(Kn) > 1 else Kn[0]


def Cc(Dp, T_degC=20, P_kPa=101.3):
    """Returns the Cunningham slip correction factor"""
    Cc_alpha, Cc_beta, Cc_gamma = 1.142, 0.558, 0.999  # Cc constants
    Kn_num = Kn(Dp, T_degC, P_kPa)
    Cc = 1 + Kn_num * (Cc_alpha + Cc_beta * np.exp(-Cc_gamma / Kn_num))

    return Cc if len(Cc) > 1 else Cc[0]


def GK_eta(Dp, L_tube, Q_lpm=0.3, T_degC=20, P_kPa=101.3):
    """Gormley-Kennedy (1949) particle transmission efficiency
    in laminar flow through a tube"""
    T_K = T_degC + 273.15
    Dp = np.array([Dp]).flatten()
    Dp_SI = Dp * 1e-9
    k_Bltz = 1.380658e-23  # Boltzmann constant [J/K]
    Dc = (
        k_Bltz
        * T_K
        * Cc(Dp, T_degC, P_kPa)
        / (3 * np.pi * mu_g(T_degC) * Dp_SI)
    )  # Diffusion coefficient [m^2/s]
    Q_SI = Q_lpm * 0.001 / 60  # flowrate [m^3/s]
    xi = Dc * (L_tube * np.pi / Q_SI)

    # next lines calculate eta for xi<0.02 or xi>0.02
    eta_xi_lt_p02 = (
        1 - 2.5638 * xi ** (2 / 3) + 1.2 * xi + 0.1767 * xi ** (4 / 3)
    )  # xi<=0.02
    eta_xi_gt_p02 = (
        0.81905 * np.exp(-3.6568 * xi)
        + 0.09753 * np.exp(-22.305 * xi)
        + 0.0325 * np.exp(-56.961 * xi)
        + 0.01544 * np.exp(-107.62 * xi)
    )  # xi>0.02
    eta = eta_xi_lt_p02 * (xi <= 0.02) + eta_xi_gt_p02 * (xi > 0.02)

    return eta if len(eta) > 1 else eta[0]


def cpc_eta_activation(x, eta, d50, d0):
    """Returns CPC activation efficiency according to Stolzenburg & McMurry (1991)
    formulation (ultrafine-CPC)"""
    x = np.array([x]).flatten()
    y = eta * (1 - np.exp(-np.log(2) * (x - d0) / (d50 - d0)))
    y[y < 0] = 0

    return y if len(y) > 1 else y[0]


def cpc_eta_activ_w_GK(x, eta, d50, d0, L=0.05, Q=0.3, T_degC=20, P_kPa=101.3):
    """Returns CPC activation efficiency multiplied with
    Gormley-Kennedy transmission efficiency"""
    y = cpc_eta_activation(x, eta, d50, d0) * GK_eta(x, L, Q, T_degC, P_kPa)
    y[y < 0] = 0

    return y if len(y) > 1 else y[0]


def calc_slip_correction(d_nm):
    """Seinfeld and Pandis 2016 (9.34), returns C_c = [1]"""
    mean_free_path = 65.1  # nm
    slip_correction = 1 + 2 * mean_free_path / d_nm * (
        1.257 + 0.4 * np.exp((-1.1 * d_nm) / (2 * mean_free_path))
    )
    return slip_correction  # if len(slip_correction) > 1 else slip_correction


def calc_diffusion_coeff(d_nm):
    """Seinfeld and Pandis (9.73), returns D = [m^2/s]"""
    k = 1.381e-23  # J/K [Boltzman Constant]
    t = 273  # K [Temperature]
    c_c = calc_slip_correction(d_nm)  # 1 [Slip Correction]
    mu = 1.72e-05  # kg/(m*s) [Dynamic Viscosity]
    d_p = d_nm * 1e-9  # m
    diffusion_coeff = (k * t * c_c) / (3 * np.pi * mu * d_p)
    return diffusion_coeff  # if len(diffusion_coeff) > 1 else (diffusion_coeff)


def correct_detect_eff(dma, diameters, dndlndp):
    """Returns inverted data corrected for CPC detection efficiency"""
    bins = diameters.shape[1]
    # Calculate CPC detection efficiency for input diameters
    if dma == "nanodma":
        cpc_fits = [8.02e-01, 1.62e00, 1.49e00, 1.22e-01]
    if dma == "longdma":
        cpc_fits = [0.95834315, 13.05058168, 10.3389279, 0.30860654]
    cpc_eff = cpc_eta_activ_w_GK(diameters, *cpc_fits)
    cpc_eff = cpc_eff.reshape(-1, bins)

    # Factor cpc detection efficiency into inversion
    cpc_eff[cpc_eff == 0] = "nan"
    dndlndp = dndlndp / cpc_eff

    return dndlndp


def correct_sampling_losses(dma, diameters, dndlndp):
    """Returns inverted data corrected for diffusion losses
    Gravitational setting loss and inertial loss both much < 1 %"""

    # Set flow and length parameters
    if dma == "nanodma":
        q_lpm = 7  # sampling flow [LPM]
        l_in = (
            1.5
            + (2 * np.pi * 0.75) * (1 / 4)
            + 4
            + 1.5
            + (2 * np.pi * 0.75) * (1 / 4)
            + 1
            + 1
        )  # inlet length [in]
    elif dma == "longdma":
        q_lpm = 1  # sampling flow [LPM]
        l_in = (
            1.5
            + (2 * np.pi * 0.75) * (1 / 4)
            + 4
            + 1.5
            + (2 * np.pi * 0.75) * (1 / 4)
            + 1
            + 1
            + 1
        )  # inlet length [in]

    # Convert units
    q_si = q_lpm * 1e-3 / 60  # sampling flow [m^3/s]
    l_si = l_in * 0.0254  # inlet length [m]

    # Calculate diffusion losses
    d = calc_diffusion_coeff(diameters)  # diffusion coefficient [m^2/s]

    mu = (d * l_si) / q_si
    eta_mu_lt_pt009 = 1 - 5.50 * mu ** (2 / 3) + 3.77 * mu
    eta_mu_gte_pt009 = 0.819 * np.exp(-11.5 * mu) + 0.0975 * np.exp(-70.1 * mu)

    eta_diff = eta_mu_lt_pt009 * (mu < 0.009) + eta_mu_gte_pt009 * (mu >= 0.009)

    # Factor into CPC detection efficiency
    dndlndp = dndlndp / eta_diff

    return dndlndp


def data_correction(dma, time_data, data):
    """Incorporate CPC detection efficiency and sampling losses into inverted data"""
    # Clean data
    data[data == np.inf] = np.nan
    data[data == -np.inf] = np.nan

    # Separate data into diameter, concentration and dndlndp
    tot_cols = data.shape[1]
    bins = int(tot_cols / 3)
    diameters = data[:, 0:bins]
    concentration = data[:, bins : 2 * bins]
    dndlndp = data[:, 2 * bins : 3 * bins]

    # Correct for CPC detection efficiency
    dndlndp = correct_detect_eff(dma, diameters, dndlndp)

    # Correct for sampling losses
    dndlndp = correct_sampling_losses(dma, diameters, dndlndp)

    # Recombine into one array
    data = np.concatenate((diameters, concentration, dndlndp), axis=1)

    # Convert a copy of array to Pandas for CSV export
    time_export = pd.DataFrame(time_data)
    data_export = pd.DataFrame(data)
    export = pd.concat([time_export, data_export], axis=1)
    return data, export
