import csv
from datetime import datetime
import numpy as np
import os
import scipy.optimize
import time
import traceback

import mobilitycalc

# import shared_var


class DataLogging:
    def __init__(
        self,
        config,
        stop_threads,
        datalog_barrier,
        close_barrier,
        file_dir_e,
        all_data,
    ):
        self.config = config
        self.stop_threads = stop_threads
        self.datalog_barrier = datalog_barrier
        self.close_barrier = close_barrier
        self.file_dir_e = file_dir_e
        self.all_data = all_data
        self.graph_line = False

    def share_graph_data(self):
        return self.graph_line

    def data_logging(self):
        dma = self.config["dma"]
        data_config = self.config["data_config"]
        key_config = self.config["keys"]
        voltage_config = self.config["voltage_set_config"]
        dlndp = self.config["voltage_set_config"]["dlnDp"]

        # Create the subfolder with current date and time
        start_time, csv_filepath, csv_filepath2 = create_files(
            dma,
            data_config["header"],
            key_config["blower"]
            + key_config["voltage_scan"]
            + key_config["voltage_monitor"]
            + key_config["cpc_counting"]
            + key_config["cpc_serial"],
            self.file_dir_e,
        )
        log_elapsed = 0
        count = 0
        start = time.monotonic()

        self.scan = {"dia": [], "conc": [], "dndlndp": []}
        self.current = {"dia": [], "conc": [], "dndlndp": []}
        self.scan_time = []
        self.prev_set_dia = 0
        self.prev_calc_dia = 0

        # Constants for update intervals
        curr_time = time.monotonic()
        update_time = 1  # seconds

        # Infinite Loop
        while not self.stop_threads.is_set():
            try:
                # Create new file on new day
                if datetime.now().day != start_time.day:
                    start_time, csv_filepath, csv_filepath2 = create_files(
                        dma,
                        data_config["header"],
                        data_config["cpc_header"],
                        self.file_dir_e,
                    )
                    log_elapsed = 0
                    count = 0
                    start = time.monotonic()

                # Increment count and elasped time
                count += 1
                log_elapsed = time.monotonic() - start

                self.datalog_barrier.wait()

                # Get variables
                try:
                    self.set_dia = self.all_data["voltset"]["dia set"]
                    self.concentration = self.all_data["count"]["concentration"]
                    self.voltage_monitor = self.all_data["voltmon"][
                        "supply_volt"
                    ]
                    self.flow_read = self.all_data["blower"]["flow"]
                except Exception as e:
                    print(e)
                    self.set_dia = np.nan
                    self.concentration = np.nan
                    self.voltage_monitor = np.nan
                    self.flow_read = np.nan

                # Calculate Diameter
                self.calculate_diameter_from_montior(voltage_config)
                # Invert data
                if self.flow_read > 0 and self.concentration != -9999:
                    self.dndlndp = invert_data(
                        self.concentration,
                        self.calculated_dia,
                        voltage_config["dma_eff_length"],
                        voltage_config["aerosol_charge"],
                        voltage_config["dma_sample_flow"],
                        self.flow_read * 1000,
                        dlndp,
                    )
                else:
                    self.dndlndp = 0

                # Construct row to export to CSV
                calc_values = [
                    datetime.now(),
                    count,
                    log_elapsed,
                    self.calculated_dia,
                    self.dndlndp,
                ]
                data_values = [
                    value
                    for sub_dict in self.all_data.values()
                    for value in sub_dict.values()
                ]

                all_values = calc_values + data_values

                # Write all raw data to CSV file
                with open(csv_filepath, mode="a", newline="") as data_file:
                    data_writer = csv.writer(data_file, delimiter=",")
                    data_writer.writerow(all_values)

                # If this is the first scan, set time
                if not self.scan_time:
                    self.scan_time.append(datetime.now())

                # If set diameter is the same, append data to list
                if self.set_dia == self.prev_set_dia:
                    self.append_diameter_repeats()

                # If set dia is larger, avg data, append to scan and reset
                elif abs(self.set_dia) > self.prev_set_dia:
                    self.average_diameter_repeats()
                    self.reset_and_append_diameter_repeat()
                    self.prev_set_dia = self.set_dia

                # If set dia is smaller, that indicates a new scan
                elif abs(self.set_dia) < self.prev_set_dia:
                    self.average_diameter_repeats()
                    list_scan_data = self.write_averaged_csv(csv_filepath2)
                    self.graph_line = list_scan_data.insert(0, self.scan_time)

                    # Re-initalize
                    self.scan_time = [datetime.now()]
                    self.reset_and_append_diameter_repeat()
                    self.prev_set_dia = self.set_dia

                else:
                    pass

                # else:
                #     # First loop
                #     self.scan["dia"].append(datetime.now())
                #     self.append_diameter_repeats
                #     previous_diameter = shared_var.set_diameter

                self.datalog_barrier.clear()

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
        self.close_barrier.wait()

    def calculate_diameter_from_montior(self, voltage_config):
        # Caluclated diameter using set diameter as a guess
        self.calculated_dia = mobilitycalc.calc_dia_from_voltage(
            self.voltage_monitor,
            self.flow_read * 1000,
            self.flow_read * 1000,
            voltage_config["dma_length"],
            voltage_config["dma_outer_radius"],
            voltage_config["dma_inner_radius"],
            self.set_dia,
        )
        # If set diameter results in negative value, use previous calculated
        if self.calculated_dia < 0 and self.prev_calc_dia != 0:
            self.calculated_dia = mobilitycalc.calc_dia_from_voltage(
                self.voltage_monitor,
                self.flow_read * 1000,
                self.flow_read * 1000,
                voltage_config["dma_length"],
                voltage_config["dma_outer_radius"],
                voltage_config["dma_inner_radius"],
                self.prev_calc_dia,
            )
        # If still negative, use 0.001 as guess
        if self.calculated_dia < 0:
            self.calculated_dia = mobilitycalc.calc_dia_from_voltage(
                self.voltage_monitor,
                self.flow_read * 1000,
                self.flow_read * 1000,
                voltage_config["dma_length"],
                voltage_config["dma_outer_radius"],
                voltage_config["dma_inner_radius"],
                0.001,
            )
        self.prev_calc_dia = self.calculated_dia

    def write_averaged_csv(self, csv_filepath2):
        """Write averaged data to CSV file
        Format: [scan_time, avg_dia, avg_conc, avg_dndlndp]"""
        # Flatten scan data dictionary to list for CSV export
        list_scan_data = [self.scan[value] for value in self.scan]
        # flat_scan_data = [item for sublist in self.scan for item in sublist]
        flat_scan_data = [
            item for sublist in self.scan.values() for item in sublist
        ]
        print(f"List scan data {list_scan_data}")
        print(f"Flast scan data {flat_scan_data}")
        # Write line to file
        with open(csv_filepath2, mode="a", newline="") as data_file:
            data_writer = csv.writer(data_file, delimiter=",")
            data_writer.writerow(self.scan_time + flat_scan_data)
        return list_scan_data

    def reset_and_append_diameter_repeat(self):
        self.current = {"dia": [], "conc": [], "dndlndp": []}
        self.append_diameter_repeats

    def append_diameter_repeats(self):
        """Creates a lists of diameter, conc, and dndlndp for current dia"""
        # Check if calculated diameter is realistic and concentration exists
        if (
            abs(self.calculated_dia) / self.set_dia > 10
            or self.concentration == -9999
        ):
            pass
        else:
            self.current["dia"].append(self.calculated_dia)
            self.current["conc"].append(self.concentration)
            self.current["dndlndp"].append(self.dndlndp)

    def average_diameter_repeats(self):
        # If calc dia exists for current dia, avg & append to current scan
        if self.current["dia"]:
            self.scan["dia"].append(
                sum(self.current["dia"]) / len(self.current["dia"])
            )
            # If conc & dndlndp exists, avg & append to current scan
            if self.current["conc"]:
                self.scan["conc"].append(
                    sum(self.current["conc"]) / len(self.current["conc"])
                )
                self.scan["dndlndp"].append(
                    sum(self.current["dndlndp"]) / len(self.current["dndlndp"])
                )
            # Else append 0's
            else:
                self.scan["conc"].append(0)
                self.scan["dndlndp"].append(0)
        # Else append set dia and 0's
        else:
            self.scan["dia"].append(self.prev_set_dia)
            self.scan["conc"].append(0)
            self.scan["dndlndp"].append(0)


# def average_diameter_repeats(
#     previous_diameter,
#     scan_data_dia,
#     scan_data_conc,
#     scan_data_dndlndp,
#     current_diameter,
#     current_conc,
#     current_dndlndp,
# ):
#     if current_diameter:
#         scan_data_dia.append(sum(current_diameter) / len(current_diameter))
#         if current_conc:
#             scan_data_conc.append(sum(current_conc) / len(current_conc))
#             scan_data_dndlndp.append(
#                 sum(current_dndlndp) / len(current_dndlndp)
#             )
#         else:
#             scan_data_conc.append(0)
#             scan_data_dndlndp.append(0)
#         current_diameter = []
#         current_conc = []
#         current_dndlndp = []
#     else:
#         scan_data_dia.append(previous_diameter)
#         scan_data_conc.append(0)
#         scan_data_dndlndp.append(0)
#     return current_diameter, current_conc, current_dndlndp


# def add_diameter_repeats(
#     current_diameter, current_conc, calculated_dia, current_dndlndp, dndlndp
# ):
#     if abs(calculated_dia) / shared_var.set_diameter > 10:
#         pass
#     else:
#         current_diameter.append(calculated_dia)
#         if shared_var.concentration == -9999:
#             pass
#         else:
#             current_conc.append(shared_var.concentration)
#             current_dndlndp.append(dndlndp)


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


def invert_data(N, d_p, l_eff_m, aerosol_charge, q_a_ccm, q_c_ccm, dlnDp):
    """Stolzenburg 2008 (Eqn. 27), returns concentration particle/(cm^3*s)"""
    # Not including CPC activation or sample tube penetration
    # if d_p < 1.00001:
    #     d_p = 1.00001
    q_a = q_a_ccm  # ccm [Aerosol Inlet Flowrate]
    q_s = q_a_ccm  # ccm [Aerosol Outlet Flowrate]
    q_c = q_c_ccm  # ccm [Sheath Flowrate]
    q_m = q_c_ccm  # ccm [Excess Flowrate]
    a_star = mobilitycalc.calc_a_star(d_p, dlnDp)
    beta = (q_s + q_a) / (q_m + q_c)
    delta = (q_s - q_a) / (q_s + q_a)
    charge_frac = mobilitycalc.calc_charged_frac(aerosol_charge, d_p)
    cpc_active_eff = 1
    dma_penetration = mobilitycalc.calc_dma_penetration(d_p, l_eff_m, q_a)
    sample_tube_penetration = 1
    penetrate_eff = dma_penetration * sample_tube_penetration
    dNdlnDp = (N * a_star) / (
        (q_a / q_s)
        * beta
        * (1 + delta)
        * charge_frac
        * cpc_active_eff
        * penetrate_eff
    )
    return dNdlnDp
