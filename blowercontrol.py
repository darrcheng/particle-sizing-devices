from labjack import ljm
import time
import sys
import traceback
from datetime import datetime

import sensors
import shared_var as shared_var


def blower(
    handle, labjack_io, stop_threads, close_barrier, sensor_config, pid, temp_e, rh_e, p_e, flow_e
):
    """Reads in sheath flow sensors, updates GUI and executes the PID control"""

    # Set flow to 0 LPM and pause to allow blower to slow down
    ljm.eWriteName(handle, labjack_io["flow_set_output"], 0)
    time.sleep(5)

    # Constants for flow intervals
    curr_time = time.monotonic()
    flow_update_time = 0.500  # seconds
    # flow_count = 0

    # Infinite Loop
    while not stop_threads.is_set():
        try:
            # Read temperature
            shared_var.temp_read = sensors.temp_update(
                handle, labjack_io["temp_input"], sensor_config["temp_factor"]
            )

            # Read RH, correct for temperature
            shared_var.rh_read = sensors.rh_update(
                handle, labjack_io["rh_input"], shared_var.temp_read
            )

            # Read Pressure
            shared_var.press_read = sensors.press_update(handle, labjack_io["press_input"])

            # Read Flow Rate
            shared_var.flow_read = sensors.flow_update(
                handle,
                labjack_io["flow_read_input"],
                sensor_config["flow_factor"],
                sensor_config["flow_offset"],
            )

            # PID Function
            control = 0.016 * shared_var.blower_flow_set + 1.8885 + pid(shared_var.flow_read)

            # Set blower voltage
            ljm.eWriteName(handle, labjack_io["flow_set_output"], control)

            shared_var.blower_runtime = time.monotonic() - curr_time - flow_update_time

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
    close_barrier.wait()
