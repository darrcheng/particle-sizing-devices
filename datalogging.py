from datetime import datetime
import time
import csv
import settings


def dataLogging(start_time, stop_threads):
    # Open CSV logging file
    with open(settings.file, mode="w", newline="") as data_file:
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
                        settings.labjackVoltage * settings.voltageFactor,
                        settings.voltageMonitor,
                        settings.temp_read,
                        settings.rh_read,
                        settings.press_read,
                    ]
                )

            except BaseException:
                print("Data Logging Error")
                break
