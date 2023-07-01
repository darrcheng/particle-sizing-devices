from datetime import datetime
import time
import csv
import shared_var
import os
import numpy as np
import scipy.optimize
import traceback

import mobilitycalc


def dataLogging(stop_threads, b, close_barrier, dma, data_config, voltage_config, file_e):
    # Create the subfolder with current date and time
    start_time, csv_filepath, csv_filepath2 = create_files(
        dma, data_config["header"], data_config["cpc_header"], file_e
    )
    log_elapsed = 0
    count = 0
    start = time.monotonic()

    scan_data_dia = []
    scan_data_conc = []
    scan_data_dndlndp = []
    current_diameter = []
    current_conc = []
    current_dndlndp = []
    previous_diameter = 0
    previous_calc_diameter = 0

    # Constants for update intervals
    curr_time = time.monotonic()
    update_time = 1  # seconds

    # Infinite Loop
    while not stop_threads.is_set():
        try:
            # Create new file on new day
            if datetime.now().day != start_time.day:
                start_time, csv_filepath, csv_filepath2 = create_files(
                    dma, data_config["header"], data_config["cpc_header"], file_e
                )
                log_elapsed = 0
                count = 0
                start = time.monotonic()

            # Increment count and elasped time
            count += 1
            log_elapsed = time.monotonic() - start

            # print("datalogging wait")
            b.wait()

            # Calculate Diameter
            calculated_dia = mobilitycalc.calc_dia_from_voltage(
                shared_var.voltage_monitor,
                shared_var.flow_read * 1000,
                shared_var.flow_read * 1000,
                voltage_config["dma_length"],
                voltage_config["dma_outer_radius"],
                voltage_config["dma_inner_radius"],
                shared_var.set_diameter,
            )
            if calculated_dia < 0 and previous_calc_diameter != 0:
                calculated_dia = mobilitycalc.calc_dia_from_voltage(
                    shared_var.voltage_monitor,
                    shared_var.flow_read * 1000,
                    shared_var.flow_read * 1000,
                    voltage_config["dma_length"],
                    voltage_config["dma_outer_radius"],
                    voltage_config["dma_inner_radius"],
                    previous_calc_diameter,
                )
            else:
                calculated_dia = mobilitycalc.calc_dia_from_voltage(
                    shared_var.voltage_monitor,
                    shared_var.flow_read * 1000,
                    shared_var.flow_read * 1000,
                    voltage_config["dma_length"],
                    voltage_config["dma_outer_radius"],
                    voltage_config["dma_inner_radius"],
                    0.001,
                )
            previous_calc_diameter = calculated_dia
            # Invert data
            if shared_var.blower_runtime > 0 and shared_var.concentration != -9999:
                dndlndp = invert_data(
                    shared_var.concentration,
                    calculated_dia,
                    voltage_config["dma_eff_length"],
                    voltage_config["aerosol_charge"],
                    voltage_config["dma_sample_flow"],
                    shared_var.blower_runtime * 1000,
                )
            else:
                dndlndp = 0

            # Write line by line data to CSV file
            with open(csv_filepath, mode="a", newline="") as data_file:
                data_writer = csv.writer(data_file, delimiter=",")
                data_writer.writerow(
                    [
                        count,
                        datetime.now(),
                        log_elapsed,
                        shared_var.set_diameter,
                        calculated_dia,
                        shared_var.ljvoltage_set_out,
                        shared_var.voltage_monitor,
                        shared_var.flow_read,
                        shared_var.temp_read,
                        shared_var.rh_read,
                        shared_var.press_read,
                        shared_var.concentration,
                        shared_var.concentration_nodead,
                        shared_var.curr_count,
                        shared_var.pulse_width,
                        shared_var.pulse_width_error,
                        shared_var.blower_runtime,
                        shared_var.voltage_runtime,
                        shared_var.voltage_monitor_runtime,
                        shared_var.cpc_counting_runtime,
                        shared_var.data_logging_runtime,
                    ]
                    + shared_var.cpc_serial_read
                )

            # Write aggregated data to CSV file
            if scan_data_dia:
                if shared_var.set_diameter == previous_diameter:
                    # Averaging over current diameter
                    add_diameter_repeats(
                        current_diameter, current_conc, calculated_dia, current_dndlndp, dndlndp
                    )
                elif abs(shared_var.set_diameter) > previous_diameter:
                    # When diameter increases, save previous diameter data
                    current_diameter, current_conc, current_dndlndp = average_diameter_repeats(
                        previous_diameter,
                        scan_data_dia,
                        scan_data_conc,
                        scan_data_dndlndp,
                        current_diameter,
                        current_conc,
                        current_dndlndp,
                    )
                    add_diameter_repeats(
                        current_diameter, current_conc, calculated_dia, current_dndlndp, dndlndp
                    )
                    previous_diameter = shared_var.set_diameter

                else:
                    # When one scan finishes, save row to file and reset
                    # print(dma)
                    current_diameter, current_conc, current_dndlndp = average_diameter_repeats(
                        previous_diameter,
                        scan_data_dia,
                        scan_data_conc,
                        scan_data_dndlndp,
                        current_diameter,
                        current_conc,
                        current_dndlndp,
                    )

                    # Write line to file
                    with open(csv_filepath2, mode="a", newline="") as data_file:
                        data_writer = csv.writer(data_file, delimiter=",")
                        data_writer.writerow(scan_data_dia + scan_data_conc + scan_data_dndlndp)
                    shared_var.graph_line = [scan_data_dia, scan_data_conc, scan_data_dndlndp]
                    # Re-initalize
                    scan_data_dia = []
                    scan_data_conc = []
                    scan_data_dndlndp = []
                    scan_data_dia.append(datetime.now())
                    add_diameter_repeats(
                        current_diameter, current_conc, calculated_dia, current_dndlndp, dndlndp
                    )
                    previous_diameter = shared_var.set_diameter

            else:
                # First loop
                scan_data_dia.append(datetime.now())
                add_diameter_repeats(
                    current_diameter, current_conc, calculated_dia, current_dndlndp, dndlndp
                )
                previous_diameter = shared_var.set_diameter

            b.reset()
            # print("barrier reset")

            shared_var.data_logging_runtime = time.monotonic() - curr_time - update_time

            # Schedule the next update
            curr_time = curr_time + update_time
            next_time = curr_time + update_time - time.monotonic()
            if next_time < 0:
                next_time = 0
                print("Slow: Data Logging" + str(datetime.now()))
            time.sleep(next_time)

        except BaseException as e:
            print("Data Logging Error")
            print(traceback.format_exc())
            # print(e)
            break
    print("Shutdown: Data Logging")
    close_barrier.wait()


def average_diameter_repeats(
    previous_diameter,
    scan_data_dia,
    scan_data_conc,
    scan_data_dndlndp,
    current_diameter,
    current_conc,
    current_dndlndp,
):
    if current_diameter:
        scan_data_dia.append(sum(current_diameter) / len(current_diameter))
        if current_conc:
            scan_data_conc.append(sum(current_conc) / len(current_conc))
            scan_data_dndlndp.append(sum(current_dndlndp) / len(current_dndlndp))
        else:
            scan_data_conc.append(0)
            scan_data_dndlndp.append(0)
        current_diameter = []
        current_conc = []
        current_dndlndp = []
    else:
        scan_data_dia.append(previous_diameter)
        scan_data_conc.append(0)
        scan_data_dndlndp.append(0)
    return current_diameter, current_conc, current_dndlndp


def add_diameter_repeats(current_diameter, current_conc, calculated_dia, current_dndlndp, dndlndp):
    if abs(calculated_dia) / shared_var.set_diameter > 10:
        pass
    else:
        current_diameter.append(calculated_dia)
        if shared_var.concentration == -9999:
            pass
        else:
            current_conc.append(shared_var.concentration)
            current_dndlndp.append(dndlndp)


def create_files(dma, header, cpc_header, file_e):
    start_time = datetime.now()
    current_date = start_time.strftime("%Y-%m-%d")
    subfolder_path = os.path.join(os.getcwd(), current_date)
    os.makedirs(subfolder_path, exist_ok=True)

    # Create CSV file and writer
    file_datetime = start_time.strftime("%Y%m%d_%H%M%S")
    csv_filename = dma + "_" + file_datetime + ".csv"
    csv_filepath = os.path.join(subfolder_path, csv_filename)
    csv_filename2 = dma + "_invert_" + file_datetime + ".csv"
    csv_filepath2 = os.path.join(subfolder_path, csv_filename2)
    file_e.delete(0, "end")
    file_e.insert(0, csv_filepath)

    # Open CSV logging file
    with open(csv_filepath, mode="w", newline="") as data_file:
        data_writer = csv.writer(data_file, delimiter=",")
        data_writer.writerow(header + cpc_header)

    return start_time, csv_filepath, csv_filepath2


def invert_data(N, d_p, l_eff_m, aerosol_charge, q_a_ccm, q_c_ccm):
    q_a = q_a_ccm  # ccm [Aerosol Inlet Flowrate]
    q_s = q_a_ccm  # ccm [Aerosol Outlet Flowrate]
    q_c = q_c_ccm  # ccm [Sheath Flowrate]
    q_m = q_c_ccm  # ccm [Excess Flowrate]
    diameters = np.array([shared_var.low_dia_lim, shared_var.high_dia_lim])
    elec_mobility = mobilitycalc.calc_mobility_from_dia(diameters)
    dlnZp = np.log(elec_mobility[1]) - np.log(elec_mobility[0])
    dlnDp = np.log(diameters[1]) - np.log(diameters[0])
    a_star = -dlnZp / dlnDp
    beta = (q_s + q_a) / (q_m + q_c)
    delta = (q_s - q_a) / (q_s + q_a)
    if d_p < 1.00001:
        d_p = 1.00001
    charge_frac = mobilitycalc.calc_charged_frac(aerosol_charge, d_p)
    cpc_active_eff = 1
    dma_penetration = mobilitycalc.calc_dma_penetration(d_p, l_eff_m, q_a)
    sample_tube_penetration = 1
    penetrate_eff = dma_penetration * sample_tube_penetration
    dNdlnDp = (N * a_star) / (
        (q_a / q_s) * beta * (1 + delta) * charge_frac * cpc_active_eff * penetrate_eff
    )
    return dNdlnDp


# def calc_charged_frac(charge, d_nm):
#     """Wiedensohler 1988, returns charged fraction"""
#     a_coeff = {
#         -2: [-26.3328, 35.9044, -21.4608, 7.0867, -1.3088, 0.1051],
#         -1: [-2.3197, 0.6175, 0.6201, -0.1105, -0.1260, 0.0297],
#         0: [-0.0003, -0.1014, 0.3073, -0.3372, 0.1023, -0.0105],
#         1: [-2.3484, 0.6044, 0.4800, 0.0013, -0.1553, 0.0320],
#         2: [-44.4756, 79.3772, -62.8900, 26.4492, -5.7480, 0.5049],
#     }
#     power_sum = []
#     for i in range(6):
#         power_sum.append((a_coeff[charge][i] * np.log10(d_nm) ** i))
#     charged_frac = 10 ** sum(power_sum)
#     return charged_frac


# def calc_slip_correction(d_nm):
#     """Seinfeld and Pandis 2016 (9.34), returns C_c"""
#     mean_free_path = 65.1  # nm
#     slip_correction = 1 + 2 * mean_free_path / d_nm * (
#         1.257 + 0.4 * np.exp((-1.1 * d_nm) / (2 * mean_free_path))
#     )
#     return slip_correction


# def calc_diffusion_coeff(d_nm):
#     """Seinfeld and Pandis (9.73), returns D = [m^2/s]"""
#     k = 1.381e-23  # J/K [Boltzman Constant]
#     t = 273  # K [Temperature]
#     c_c = mobilitycalc.calc_slip_correction(d_nm)  # 1 [Slip Correction]
#     mu = 1.72e-05  # kg/(m*s) [Dynamic Viscosity]
#     d_p = d_nm * 1e-9  # m
#     diffusion_coeff = (k * t * c_c) / (3 * np.pi * mu * d_p)
#     return diffusion_coeff


# def calc_deposition_param(d_nm, l_eff_m, q_sample_sccm):
#     """Jiang 2011 (Eqn. 8), returns mu"""
#     d = mobilitycalc.calc_diffusion_coeff(d_nm)  # m^2/s [Diffusion coefficient]
#     q_cm_s = q_sample_sccm / 60  # cm^3/s
#     q_m_s = q_cm_s * 1e-6  # m^3/s
#     deposition_param = (np.pi * d * l_eff_m) / q_m_s
#     return deposition_param


# def calc_dma_penetration(d_nm, l_eff_m, q_sample_sccm):
#     """Jiang 2011 (Eqn. 9 & 10), returns dma penetration efficiency"""
#     mu = mobilitycalc.calc_deposition_param(
#         d_nm, l_eff_m, q_sample_sccm
#     )  # 1 [Deposition Parameter]
#     if mu > 0.02:
#         penetration_eff = (
#             0.819 * np.exp(-3.66 * mu)
#             + 0.0975 * np.exp(-22.3 * mu)
#             + 0.0325 * np.exp(-57.0 * mu)
#             + 0.0154 * np.exp(-107.6 * mu)
#         )
#     else:
#         penetration_eff = 1.0 - 2.56 * mu ** (2 / 3) + 1.2 * mu + 0.1767 * mu ** (4 / 3)
#     return penetration_eff


# def calc_mobility_from_voltage(volt, q_sheath_ccm, q_excess_ccm, dma_l_cm, dma_od_cm, dma_id_cm):
#     """Stolzenburg 2008 (Eqn. 1 & 3), returns electrical mobility cm^2/(V*s)"""
#     q_sheath = q_sheath_ccm / 60  # cm^3/s
#     q_excess = q_excess_ccm / 60  # cm^3/s
#     elec_mobility = (
#         (q_sheath + q_excess) / (4 * np.pi * volt * dma_l_cm) * np.log(dma_od_cm / dma_id_cm)
#     )
#     return elec_mobility


# def calc_voltage_from_mobility(
#     mobil_cm, q_sheath_ccm, q_excess_ccm, dma_l_cm, dma_od_cm, dma_id_cm
# ):
#     """Stolzenburg 2008 (Eqn. 1 & 3), returns electrical mobility cm^2/(V*s)"""
#     q_sheath = q_sheath_ccm / 60  # cm^3/s
#     q_excess = q_excess_ccm / 60  # cm^3/s
#     volt = (q_sheath + q_excess) / (4 * np.pi * mobil_cm * dma_l_cm) * np.log(dma_od_cm / dma_id_cm)
#     return volt


# def calc_mobility_from_dia(d_nm):
#     """Seinfeld and Pandis 2016 (9.50), returns electrical mobility cm^2/(V*s)"""
#     q = 1.60e-19  # C [1 elementary charge]
#     mu = 1.72e-05  # kg/(m*s) [Dynamic Viscosity]
#     c_c = mobilitycalc.calc_slip_correction(d_nm)  # 1 [Slip Correction]
#     elec_mobility = (q * c_c) / (3 * np.pi * mu * d_nm * 1e-9)
#     elec_mobility_cm = elec_mobility * 1e4
#     return elec_mobility_cm


# def calc_dia_from_mobility(elec_mobility_cm, d_set):
#     def calc_mobility_from_dia1(d_nm):
#         """Seinfeld and Pandis 2016 (9.50), returns electrical mobility cm^2/(V*s)"""
#         q = 1.60217663e-19  # C [1 elementary charge]
#         mu = 1.72e-05  # kg/(m*s) [Dynamic Viscosity]
#         mean_free_path = 65.1  # nm
#         return (
#             elec_mobility_cm
#             - (
#                 q
#                 * (
#                     1
#                     + 2
#                     * mean_free_path
#                     / d_nm
#                     * (1.257 + 0.4 * np.exp((-1.1 * d_nm) / (2 * mean_free_path)))
#                 )
#             )
#             / (3 * np.pi * mu * d_nm * 1e-9)
#             * 1e4
#         )

#     sol = scipy.optimize.fsolve(calc_mobility_from_dia1, d_set)
#     return sol[0]


# def calc_dia_from_voltage(volt, q_sheath_ccm, q_excess_ccm, dma_l_cm, dma_od_cm, dma_id_cm, d_set):
#     elec_mobility_cm = calc_mobility_from_voltage(
#         volt, q_sheath_ccm, q_excess_ccm, dma_l_cm, dma_od_cm, dma_id_cm
#     )
#     d_nm = mobilitycalc.calc_dia_from_mobility(elec_mobility_cm, d_set)
#     return d_nm
