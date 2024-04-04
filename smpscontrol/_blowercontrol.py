from datetime import datetime
import sys
import threading
import time
import traceback

from labjack import ljm

from . import sensors

# import shared_var as shared_var


class BlowerControl:
    def __init__(
        self,
        handle,
        config,
        stop_threads,
        close_barrier,
        blower_queue,
        labjack_counting,
        # labjack_condition,
        # labjack_pulse,
    ):
        self.handle = handle
        self.config = config
        self.stop_threads = stop_threads
        self.close_barrier = close_barrier
        self.blower_queue = blower_queue
        # self.labjack_condition = labjack_condition
        # self.labjack_pulse = labjack_pulse
        self.labjack_counting = labjack_counting

        self.thread = threading.Thread(target=self.blower)  # , args=(self.pid))

    def start(self):
        self.thread.start()

    def set_pid(self, pid):
        self.pid = pid

    def blower(self):
        """Reads in sheath flow sensors, updates GUI and executes the PID control"""
        labjack_io = self.config["labjack_io"]
        sensor_config = self.config["sensor_config"]
        gui_config = self.config["gui_config"]

        # Set flow to 0 LPM and pause to allow blower to slow down
        ljm.eWriteName(
            self.handle,
            labjack_io["flow_set_output"],
            sensor_config["flow_start"],
        )
        time.sleep(5)

        # Constants for flow intervals
        curr_time = time.monotonic()
        flow_update_time = 1  # seconds

        # Infinite Loop
        while not self.stop_threads.is_set():
            try:
                # with self.labjack_condition:
                #     self.condition.wait_for(lambda: self.labjack_pulse)
                self.labjack_counting.wait()
                # Read temperature
                temp_read = sensors.temp_update(
                    self.handle,
                    labjack_io["temp_input"],
                    sensor_config["temp_factor"],
                )

                # Read RH, correct for temperature
                rh_read = sensors.rh_update(
                    self.handle, labjack_io["rh_input"], temp_read
                )

                # Read Pressure
                press_read = sensors.press_update(
                    self.handle, labjack_io["press_input"]
                )

                # Read Flow Rate
                flow_read = sensors.flow_update(
                    self.handle,
                    labjack_io["flow_read_input"],
                    sensor_config["flow_factor"],
                    sensor_config["flow_offset"],
                )
                # print(gui_config["blower_flow_set"])
                # PID Function
                control = (
                    0.016 * gui_config["blower_flow_set"]
                    + 1.8885
                    + self.pid(flow_read)
                )
                # Set blower voltage
                ljm.eWriteName(
                    self.handle, labjack_io["flow_set_output"], control
                )

                blower_runtime = time.monotonic() - curr_time - flow_update_time

                # Add results into dictionary
                blower_data = {
                    "blower thread time": datetime.now(),
                    "temp": temp_read,
                    "rh": rh_read,
                    "press": press_read,
                    "flow": flow_read,
                    "blower runtime": blower_runtime,
                }
                self.blower_queue.put(blower_data)

                # Schedule the next update
                curr_time = curr_time + flow_update_time
                next_time = curr_time + flow_update_time - time.monotonic()
                if next_time < 0:
                    next_time = 0
                time.sleep(next_time)

            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print("Sheath Flow Sensors: " + str(ljme) + str(datetime.now()))
                time.sleep(1)

            except BaseException as e:
                print("Sheath Flow Sensor Error")
                print(traceback.format_exc())
                break

        print("Shutdown: Sheath Flow Sensors")
        self.close_barrier.wait()
