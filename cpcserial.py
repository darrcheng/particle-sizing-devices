import time
from datetime import datetime  # Pulls current time from system
import shared_var as shared_var
import traceback
import serial


# Define Voltage Monitor
def serial_read(stop_threads, close_barrier, data_config):
    # Constants for cpc serial intervals
    curr_time = time.monotonic()
    update_time = 1  # seconds

    # Set up the serial port
    ser = serial.Serial(
        port=data_config["serial_port"],
        baudrate=data_config["serial_baud"],
        bytesize=data_config["serial_bytesize"],
        parity=data_config["serial_parity"],
        timeout=data_config["serial_timeout"],
    )
    ser.flushInput()

    # Send startup commands
    if data_config["start_commands"]:
        for start_command in data_config["start_commands"]:
            ser.write((start_command + "\r").encode())
            ser.readline().decode().rstrip()

    # Send commands and record responses
    commands = data_config["serial_commands"]

    while not stop_threads.is_set():
        try:
            # Store responses in a list
            responses = []

            for command in commands:
                # Send command to serial port
                ser.write((command + "\r").encode())

                # Read response from serial port
                response = ser.readline().decode().rstrip()
                response = response.split(",")

                # Append response to the list
                responses.extend(response)

            # Share CPC data with other threads
            shared_var.cpc_serial_read = [datetime.now()] + responses
            shared_var.fill_status = responses[data_config["fill_index"]]

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
