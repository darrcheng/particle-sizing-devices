from labjack import ljm
import time

import sensors
import shared_var as shared_var


def blower(handle, labjack_io, stop_threads, sensor_config, pid, temp_e, rh_e, p_e, flow_e):
    """Reads in sheath flow sensors, updates GUI and executes the PID control"""

    # Set flow to 0 LPM and pause to allow blower to slow down
    ljm.eWriteName(handle, labjack_io["flow_set_output"], 0)
    time.sleep(5)

    # Constants for flow intervals
    curr_time = time.monotonic()
    flow_update_time = 0.200  # seconds
    # flow_count = 0

    # Infinite Loop
    while True:
        try:
            # Break out of loop on close
            if stop_threads.is_set() == True:
                print("Shutdown: Sheath Flow Sensors")
                break

            # Read temperature and update GUI
            shared_var.temp_read = sensors.temp_update(
                handle, labjack_io["temp_input"], sensor_config["temp_factor"]
            )
            temp_e.delete(0, "end")
            temp_e.insert(0, shared_var.temp_read)

            # Read RH, correct for temperature and update GUI
            shared_var.rh_read = sensors.rh_update(
                handle, labjack_io["rh_input"], shared_var.temp_read
            )
            rh_e.delete(0, "end")
            rh_e.insert(0, shared_var.rh_read)

            # Read Pressure and update GUI
            shared_var.press_read = sensors.press_update(handle, labjack_io["press_input"])
            p_e.delete(0, "end")
            p_e.insert(0, shared_var.press_read)

            # Read Flow Rate and update GUI
            shared_var.flow_read = sensors.flow_update(
                handle,
                labjack_io["flow_read_input"],
                sensor_config["flow_factor"],
                sensor_config["flow_offset"],
            )
            flow_e.delete(0, "end")
            flow_e.insert(0, shared_var.flow_read)

            # PID Function
            control = 0.016 * shared_var.blower_flow_set + 1.8885 + pid(shared_var.flow_read)

            # Set blower voltage
            ljm.eWriteName(handle, labjack_io["flow_set_output"], control)

            # Schedule the next update
            curr_time = curr_time + flow_update_time
            next_time = curr_time + flow_update_time - time.monotonic()
            if next_time < 0:
                next_time = 0
            time.sleep(next_time)

        except BaseException as e:
            print("Sheath Flow Sensor Error")
            print(e)
            break
