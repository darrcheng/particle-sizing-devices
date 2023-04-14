from labjack import ljm
import time

import sensors
import settings as settings


def blower(handle, labjack_io, stop_threads, pid, temp_e, rh_e, p_e, flow_e):
    """Reads in sheath flow sensors, updates GUI and executes the PID control"""

    # Set flow to 0 LPM and pause to allow blower to slow down
    # tdac_flow.update(0,0)
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
            settings.temp_read = sensors.temp_update(handle, labjack_io["temp_input"])
            temp_e.delete(0, "end")
            temp_e.insert(0, settings.temp_read)

            # Read RH, correct for temperature and update GUI
            settings.rh_read = sensors.rh_update(handle, labjack_io["rh_input"]) / (
                1.0546 - 0.00216 * settings.temp_read
            )
            rh_e.delete(0, "end")
            rh_e.insert(0, settings.rh_read)

            # Read Pressure and update GUI
            settings.press_read = sensors.press_update(handle, labjack_io["press_input"])
            p_e.delete(0, "end")
            p_e.insert(0, settings.press_read)

            # Read Flow Rate and update GUI
            settings.flow_read = sensors.flow_update(handle, labjack_io["flow_read_input"])
            flow_e.delete(0, "end")
            flow_e.insert(0, settings.flow_read)

            # PID Function
            control = 0.016 * settings.blower_flow_set + 1.8885 + pid(settings.flow_read)

            # Set blower voltage
            ljm.eWriteName(handle, labjack_io["flow_set_output"], control)

            # Schedule the next update
            curr_time = curr_time + flow_update_time
            next_time = curr_time + flow_update_time - time.monotonic()
            if next_time < 0:
                next_time = 0
            time.sleep(next_time)

        except BaseException:
            print("Sheath Flow Sensor Error")
            break
