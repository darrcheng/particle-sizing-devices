from datetime import datetime
import time
import csv
import shared_var
import os


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
                    ]
                )

            # Write aggregated data to CSV file
            if scan_data_dia:
                if shared_var.set_diameter == previous_diameter:
                    # Averaging over current diameter
                    current_diameter.append(shared_var.set_diameter)
                    current_conc.append(shared_var.concentration)
                elif abs(shared_var.set_diameter) > previous_diameter:
                    # When diameter increases, save previous diameter data
                    scan_data_dia.append(sum(current_diameter) / len(current_diameter))
                    current_diameter = []
                    current_diameter.append(shared_var.set_diameter)

                    scan_data_conc.append(sum(current_conc) / len(current_conc))
                    current_conc = []
                    current_conc.append(shared_var.concentration)

                    previous_diameter = shared_var.set_diameter
                else:
                    # When one scan finishes, save row to file and reset
                    scan_data_dia.append(sum(current_diameter) / len(current_diameter))
                    scan_data_conc.append(sum(current_conc) / len(current_conc))

                    with open(csv_filepath2, mode="a", newline="") as data_file:
                        data_writer = csv.writer(data_file, delimiter=",")
                        data_writer.writerow(scan_data_dia + scan_data_conc)

                    scan_data_dia = []
                    scan_data_dia.append(datetime.now())
                    current_diameter = []
                    current_diameter.append(shared_var.set_diameter)

                    scan_data_conc = []
                    current_conc = []
                    current_conc.append(shared_var.concentration)

                    previous_diameter = shared_var.set_diameter
                    print("new_line")
            else:
                # First loop
                scan_data_dia.append(datetime.now())
                current_diameter.append(shared_var.set_diameter)
                current_conc.append(shared_var.concentration)
                previous_diameter = shared_var.set_diameter

            b.reset()

            # Schedule the next update
            curr_time = curr_time + update_time
            next_time = curr_time + update_time - time.monotonic()
            if next_time < 0:
                next_time = 0
                print("Slow: Data Logging")
            time.sleep(next_time)

        except BaseException as e:
            print("Data Logging Error")
            print(e)
            break
