from datetime import datetime
import time
import csv
import shared_var
import os


def dataLogging(start_time, stop_threads, dma, file_e):
    # Create the subfolder with current date and time
    current_datetime = time.strftime("%Y-%m-%d")
    subfolder_path = os.path.join(os.getcwd(), current_datetime)
    os.makedirs(subfolder_path, exist_ok=True)

    # Create CSV file and writer
    file_datetime = time.strftime("%Y%m%d_%H%M%S")
    csv_filename = dma + file_datetime + ".csv"
    csv_filepath = os.path.join(subfolder_path, csv_filename)
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
                "Pulse Width Error [%]"
            ]
        )
        log_time = start_time
        log_elapsed = 0
        count = 0
        start = time.monotonic()

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

                # Schedule the next update
                curr_time = curr_time + update_time
                next_time = curr_time + update_time - time.monotonic()
                if next_time < 0:
                    next_time = 0
                time.sleep(next_time)

                # Write Data to CSV file
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
                        shared_var.pulse_width_error
                    ]
                )

            except BaseException as e:
                print("Data Logging Error")
                print(e)
                break
