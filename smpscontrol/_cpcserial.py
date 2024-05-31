import time
from datetime import datetime  # Pulls current time from system
import threading
import traceback
import serial


class CPCSerial:
    def __init__(
        self, config, stop_threads, close_barrier, serial_queue, fill_queue
    ):
        self.config = config
        self.stop_threads = stop_threads
        self.close_barrier = close_barrier
        self.serial_queue = serial_queue
        self.fill_queue = fill_queue

        self.thread = threading.Thread(target=self.serial_read)

    def start(self):
        self.thread.start()

    # Define Voltage Monitor
    def serial_read(self):
        data_config = self.config["data_config"]

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

        while not self.stop_threads.is_set():
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

                # Print response to screen once every 10 minutes
                if time.monotonic() % (10 * 60) < update_time:
                    print(responses)

                # # Share CPC data with other threads
                # shared_var.cpc_serial_read = [datetime.now()] + responses
                # shared_var.fill_status = responses[data_config["fill_index"]]

                # Update fill status queue
                if self.fill_queue.full():
                    self.fill_queue.get_nowait()
                self.fill_queue.put(responses[data_config["fill_index"]])

                # Calculate runtime
                serial_runtime = time.monotonic() - curr_time - update_time

                # Create dictionary of serial data
                responses = [datetime.now()] + responses + [serial_runtime]
                serial_data = dict(
                    zip(self.config["keys"]["cpc_serial"], responses)
                )
                # serial_data = {
                #     "cpc serial thread time": datetime.now(),
                #     **serial_data,
                #     "serial runtime": serial_runtime,
                # }
                self.serial_queue.put(serial_data)

                # Schedule the next update
                curr_time = curr_time + update_time
                next_time = curr_time + update_time - time.monotonic()
                if next_time < 0:
                    next_time = 0
                    print("Slow: CPC Serial Read" + str(datetime.now()))
                time.sleep(next_time)

            except BaseException as e:
                print("CPC Serial Read Error")
                print(traceback.format_exc())
                break

        print("Shutdown: CPC Serial Read")
        ser.close()
        self.close_barrier.wait()
