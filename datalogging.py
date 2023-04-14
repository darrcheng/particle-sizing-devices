from datetime import datetime
import time
import csv
import settings
import os


def dataLogging(start_time, stop_threads):
    # Create the subfolder with current date and time
    current_datetime = time.strftime("%Y-%m-%d")
    subfolder_path = os.path.join(os.getcwd(), current_datetime)
    os.makedirs(subfolder_path, exist_ok=True)

    # Create CSV file and writer
    file_datetime = time.strftime("%Y%m%d_%H%M%S")
    csv_filename = settings.dma + file_datetime + ".csv"
    csv_filepath = os.path.join(subfolder_path, csv_filename)

    # Open CSV logging file
    with open(csv_filepath, mode="w", newline="") as data_file:
        data_writer = csv.writer(data_file, delimiter=",")
        data_writer.writerow(
            [
                "Count",
                "Timer",
                "Elapsed Time",
                "Flow Rate [LPM]",
                "Set Voltage [V]",
                "Actual Voltage[V]",
                "Temperature [C]",
                "RH[%]",
                "Pressure[kPa]",
            ]
        )
        log_time = start_time
        log_elapsed = 0
        count = 0
        start = time.monotonic()

        # Constants for update intervals
        curr_time = time.monotonic()
        update_time = 0.500  # seconds

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
                        settings.flow_read,
                        settings.ljvoltage_set_out * settings.voltage_set_scaling,
                        settings.voltage_monitor,
                        settings.temp_read,
                        settings.rh_read,
                        settings.press_read,
                    ]
                )

            except BaseException:
                print("Data Logging Error")
                break
