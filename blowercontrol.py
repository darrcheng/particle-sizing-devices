from labjack import ljm
import time
from datetime import datetime  # Pulls current time from system
import sensors


# Controls the blower with PID code to ensure the flow rate stays at the specified flow rate
def blower(handle, labjack_io, stopThreads, pid, temp_e, rh_e, p_e, flow_e, blowerFlow):
    global tempRead
    global rhRead
    global pRead
    global measured

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
            if stopThreads == True:
                print("Shutdown: Sheath Flow Sensors")
                break

            # # Pause until time to start next iteration
            # flow_milliseconds = 0
            # while flow_milliseconds < flow_update_time:
            #     flow_time_new = datetime.now()
            #     flow_milliseconds = (
            #         int((flow_time_new - flow_time).total_seconds() * 1000)
            #         - flow_count * flow_update_time
            #     )
            #     time.sleep(0.001)
            # flow_count += 1

            # Read temperature and update GUI
            tempRead = sensors.temp_update(handle, labjack_io["temp_input"])
            temp_e.delete(0, "end")
            temp_e.insert(0, tempRead)

            # Read RH, correct for temperature and update GUI
            rhRead = sensors.rh_update(handle, labjack_io["rh_input"]) / (
                1.0546 - 0.00216 * tempRead
            )
            rh_e.delete(0, "end")
            rh_e.insert(0, rhRead)

            # Read Pressure and update GUI
            pRead = sensors.press_update(handle, labjack_io["press_input"])
            p_e.delete(0, "end")
            p_e.insert(0, pRead)

            # Read Flow Rate and update GUI
            flowRead = sensors.flow_update(handle, labjack_io["flow_read_input"])
            flow_e.delete(0, "end")
            flow_e.insert(0, flowRead)

            # PID Function
            measured = sensors.flow_update(handle, labjack_io["flow_read_input"])
            control = 0.016 * blowerFlow + 1.8885 + pid(measured)

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
