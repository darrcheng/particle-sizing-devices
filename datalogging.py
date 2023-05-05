from datetime import datetime
import time
import csv
import shared_var
import os
import numpy as np


def dataLogging(start_time, stop_threads, b, dma, file_e):
    # Create the subfolder with current date and time
    current_datetime = time.strftime("%Y-%m-%d")
    subfolder_path = os.path.join(os.getcwd(), current_datetime)
    os.makedirs(subfolder_path, exist_ok=True)

    # Create CSV file and writer
    file_datetime = time.strftime("%Y%m%d_%H%M%S")
    csv_filename = dma + "_" + file_datetime + ".csv"
    csv_filepath = os.path.join(subfolder_path, csv_filename)
    csv_filename2 = dma + "_invert_" + file_datetime + ".csv"
    csv_filepath2 = os.path.join(subfolder_path, csv_filename2)
    file_e.insert(0, csv_filepath)

    # Open CSV logging file
    with open(csv_filepath, mode="w", newline="") as data_file:
        data_writer = csv.writer(data_file, delimiter=",")
        data_writer.writerow(
            [
                "Count",
                "Timer",
                "Elapsed Time",
                "Set Diameter [nm]",
                "Set Voltage [V]",
                "Actual Voltage[V]",
                "Flow Rate [LPM]",
                "Temperature [C]",
                "RH[%]",
                "Pressure[kPa]",
                "Concentration[#/cc]",
                "Counts [#]",
                "Pulse Width [s]",
                "Pulse Width Error [%]",
                "Blower Control Runtime [s]",
                "Voltage Update Runtime [s]",
                "Voltage Monitor Runtime [s]",
                "CPC Counting Runtime [s]",
                "Datalogging Runtime[s]",
            ]
        )
    log_elapsed = 0
    count = 0
    start = time.monotonic()

    scan_data_dia = []
    scan_data_conc = []
    current_diameter = []
    current_conc = []
    previous_diameter = 0

    # Constants for update intervals
    curr_time = time.monotonic()
    update_time = 1  # seconds

    # Infinite Loop
    while True:
        try:
            # Break out of loop on program close
            if stop_threads.is_set() == True:
                print("Shutdown: Data Logging")
                break

            # Increment count and elasped time
            count += 1
            log_elapsed = time.monotonic() - start

            print("datalogging wait")
            b.wait()

            # Write line by line data to CSV file
            with open(csv_filepath, mode="a", newline="") as data_file:
                data_writer = csv.writer(data_file, delimiter=",")
                data_writer.writerow(
                    [
                        count,
                        datetime.now(),
                        log_elapsed,
                        shared_var.set_diameter,
                        shared_var.ljvoltage_set_out,
                        shared_var.voltage_monitor,
                        shared_var.flow_read,
                        shared_var.temp_read,
                        shared_var.rh_read,
                        shared_var.press_read,
                        shared_var.concentration,
                        shared_var.curr_count,
                        shared_var.pulse_width,
                        shared_var.pulse_width_error,
                        shared_var.blower_runtime,
                        shared_var.voltage_runtime,
                        shared_var.voltage_monitor_runtime,
                        shared_var.cpc_counting_runtime,
                        shared_var.data_logging_runtime,
                    ]
                )

            # Write aggregated data to CSV file
            if scan_data_dia:
                if shared_var.set_diameter == previous_diameter:
                    # Averaging over current diameter
                    current_diameter.append(shared_var.set_diameter)
                    if shared_var.concentration == -9999:
                        pass
                    else:
                        current_conc.append(shared_var.concentration)
                elif abs(shared_var.set_diameter) > previous_diameter:
                    # When diameter increases, save previous diameter data
                    previous_diameter = shared_var.set_diameter

                    scan_data_dia.append(sum(current_diameter) / len(current_diameter))
                    current_diameter = []
                    current_diameter.append(shared_var.set_diameter)

                    if current_conc:
                        scan_data_conc.append(sum(current_conc) / len(current_conc))
                    current_conc = []
                    if shared_var.concentration == -9999:
                        pass
                    else:
                        current_conc.append(shared_var.concentration)

                else:
                    # When one scan finishes, save row to file and reset
                    print(dma)
                    scan_data_dia.append(sum(current_diameter) / len(current_diameter))
                    if current_conc:
                        scan_data_conc.append(sum(current_conc) / len(current_conc))

                    with open(csv_filepath2, mode="a", newline="") as data_file:
                        data_writer = csv.writer(data_file, delimiter=",")
                        data_writer.writerow(scan_data_dia + scan_data_conc)

                    previous_diameter = shared_var.set_diameter

                    scan_data_dia = []
                    scan_data_dia.append(datetime.now())
                    current_diameter = []
                    current_diameter.append(shared_var.set_diameter)

                    scan_data_conc = []
                    current_conc = []
                    if shared_var.concentration == -9999:
                        pass
                    else:
                        current_conc.append(shared_var.concentration)

            else:
                # First loop
                scan_data_dia.append(datetime.now())
                current_diameter.append(shared_var.set_diameter)
                current_conc.append(shared_var.concentration)
                previous_diameter = shared_var.set_diameter

            b.reset()
            print("barrier reset")

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
            print(e)
            break


def invert_data(N, d_p):
    mean_free_path = 0.0651  # um
    charge = 1.60e-19  # coloumbs
    dyn_viscosity = 1.72e-05  # kg/(m*s)
    q_a = 1500  # ccm
    q_s = 1500  # ccm
    q_c = 15000  # ccm
    q_m = 15000  # ccm
    charge = -1
    # dma_length = voltage_config["dma_length"]  # cm
    # dma_outer_radius = voltage_config["dma_outer_radius"]  # cm
    # dma_inner_radius = voltage_config["dma_inner_radius"]  # cm
    # dma_sheath = shared_var.blower_flow_set * 1000  # sccm
    # if shared_var.diameter_mode == "dia_list":
    #     diameters = np.array(shared_var.dia_list, dtype=float)
    #     shared_var.size_bins = len(diameters)
    #     shared_var.low_dia_lim = min(diameters)
    #     shared_var.high_dia_lim = max(diameters)
    # else:
    #     diameters = np.logspace(
    #         np.log(shared_var.low_dia_lim),
    #         np.log(shared_var.high_dia_lim),
    #         num=shared_var.size_bins,
    #         base=np.exp(1),
    #     )
    #     print(diameters)
    diameters = np.array([shared_var.low_dia_lim, shared_var.high_dia_lim])
    diameters = diameters / 1000  # nm -> um
    slip_correction = 1 + 2 * mean_free_path / diameters * (
        1.257 + 0.4 * np.exp((-1.1 * diameters) / (2 * mean_free_path))
    )
    elec_mobility = (
        (charge * slip_correction) / (3 * np.pi * dyn_viscosity * diameters * 1e-6) * 1e4
    )
    dlnZp = np.log(elec_mobility[1]) - np.log(elec_mobility[0])
    dlnDp = np.log(diameters[1]) - np.log(diameters[0])
    a_star = -dlnZp / dlnDp
    beta = (q_s + q_a) / (q_m + q_c)
    delta = (q_s - q_a) / (q_s + q_a)
    charge_frac = calc_charged_frac(-1, d_p)
    cpc_active_eff = d_p * 1
    penetrate_eff = d_p * 1
    dNdlnDp = (N * a_star) / (
        (q_a / q_s) * beta * (1 + delta) * charge_frac * cpc_active_eff * penetrate_eff
    )
    return dNdlnDp


def calc_charged_frac(charge, d_nm):
    # Wiedensohler 1988
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
