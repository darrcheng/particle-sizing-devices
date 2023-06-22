import time
from datetime import datetime  # Pulls current time from system
import numpy as np
import shared_var as shared_var
import sensors
import sys
import threading
import traceback

import serial
import csv


# Define Voltage Monitor
def serial_read(stop_threads, close_barrier, data_config):
    # Constants for voltage set intervals
    curr_time = time.monotonic()
    update_time = 0.500  # seconds

    # Set up the serial port
    ser = serial.Serial(
        port=data_config["serial_port"],
        baudrate=data_config["serial_baud"],
        bytesize=data_config["serial_bytesize"],
        parity=data_config["serial_parity"],
        timeout=data_config["serial_timeout"],
    )
    ser.flushInput()

    # Send commands and record responses
    # commands = ["RALL", "RSF", "RIF","RSN","RCOUNT1","RCOUNT2"]  # Add more commands as needed
    commands = data_config["serial_commands"]

    while not stop_threads.is_set():
        try:
            # Store responses in a list
            responses = []

            for command in commands:
                # Send command to serial port
                # print(1)
                ser.write((command + "\r").encode())
                # cmd = "rall\r"
                # ser.write(cmd.encode())
                # print(2)
                # print(ser.readline())
                # Read response from serial port
                response = ser.readline().decode().rstrip()
                response = response.split(",")
                # print(3)
                # Append response to the list
                responses.extend(response)
            print(responses)

            # Calculate runtime
            shared_var.serial_runtime = time.monotonic() - curr_time - update_time

            # Schedule the next update
            curr_time = curr_time + update_time
            next_time = curr_time + update_time - time.monotonic()
            if next_time < 0:
                # if abs(next_time) / update_time > 1:
                #     curr_time = curr_time + update_time * int(abs(next_time) / update_time)
                next_time = 0
                print("Slow: CPC Serial Read" + str(datetime.now()))
            time.sleep(next_time)

        except BaseException as e:
            print("CPC Serial Read Error")
            print(traceback.format_exc())
            break

    print("Shutdown: CPC Serial Read")
    ser.close()
    close_barrier.wait()


# # Set up the CSV file
# filename = "data.csv"
# # 3772
# # header = ["time", "concentration","instrument errors","saturator temp","condensor temp","optics temp", "cabinet temp","ambient pressure","orifice pressure","nozzle pressure","laser current","liquid level","aersol flow", "inlet flow","serial number"]  # Customize the header as needed
# # 3025
# header = [
#     "time",
#     "concentration",
#     "condensor temp",
#     "saturator temp",
#     "optics temp",
#     "flow",
#     "ready environment",
#     "reference detector voltage",
#     "detector voltage",
#     "pump control value",
#     "1 second counts",
#     "liquid level",
# ]
# with open(filename, mode="w", newline="") as csv_file:
#     writer = csv.writer(csv_file)
#     writer.writerow(header)

# while True:
#     try:
#         # Write responses to CSV file
#         with open(filename, mode="a", newline="") as csv_file:
#             writer = csv.writer(csv_file)
#             writer.writerow([time.time()] + responses)

#         # Wait one second before sending the commands again
#         time.sleep(1)
#     except KeyboardInterrupt:
#         break

# # Close the serial port
