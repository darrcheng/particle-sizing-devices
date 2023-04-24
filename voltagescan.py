from labjack import ljm
import time
from datetime import datetime  # Pulls current time from system
import shared_var as shared_var
import sensors


# Controls the DMA voltage scanning
def hv(handle, labjack_io, stop_threads, voltage_scan, voltage_config, voltageSetPoint_e):
    # Set variables based on GUI inputs
    voltage = int(shared_var.low_voltage_lim)
    increment = shared_var.interval
    labjackVoltage = voltage / voltage_config["voltage_set_factor"]
    labjackIncrement = increment / voltage_config["voltage_set_factor"]

    # Constants for flow intervals
    curr_time = time.monotonic()
    update_time = shared_var.voltage_update_time / 1000  # seconds

    while True:
        try:
            # Break out of loop on close
            if stop_threads.is_set() == True:
                print("Shutdown: Voltage Set")
                break

            # If voltageCycle is on, cycle through voltages
            while voltage_scan.is_set() == False:
                # Break out of loop on close
                if stop_threads.is_set() == True:
                    print("Shutdown: Voltage Set")
                    break

                # Constants for voltage intervals
                voltage_time = datetime.now()
                voltage_count = 0

                # Reset Labjack Voltage
                labjackVoltage = 0

                # Loop through voltages between upper and lower limits
                for i in range(int(shared_var.interval)):
                    # Break out of loop on close
                    if stop_threads.is_set() == True:
                        print("Shutdown: Voltage Set")
                        break

                    # Stop cycle at current voltage if voltage cycle is turned off
                    if voltage_scan.is_set() == True:
                        break

                    # Set Voltage to Labjack and update GUI
                    ljm.eWriteName(handle, labjack_io["voltage_set_output"], labjackVoltage)
                    shared_var.ljvoltage_set_out = (
                        labjackVoltage * voltage_config["voltage_set_factor"]
                    )
                    voltageSetPoint_e.delete(0, "end")
                    voltageSetPoint_e.insert(0, shared_var.ljvoltage_set_out)

                    # Schedule the next update
                    curr_time = curr_time + update_time
                    next_time = curr_time + update_time - time.monotonic()
                    if next_time < 0:
                        next_time = 0
                    time.sleep(next_time)

                    labjackVoltage += labjackIncrement

            # If voltage cycle is turned off, set HV supply to paused voltage
            while voltage_scan.is_set() == True:
                # Break out of loop on close
                if stop_threads.is_set() == True:
                    print("Shutdown: Voltage Set")
                    break

                # Send voltage to Labjack
                ljm.eWriteName(handle, labjack_io["voltage_set_output"], labjackVoltage)

        except BaseException as e:
            print("Voltage Scan Error")
            print(e)
            break


# Define Voltage Monitor
def vIn(handle, labjack_io, stop_threads, sensor_config, supplyVoltage_e):
    # Constants for flow intervals
    curr_time = time.monotonic()
    update_time = 0.200  # seconds

    while True:
        try:
            # Break out of loop on program close
            if stop_threads.is_set() == True:
                print("Shutdown: Voltage Monitor")
                break

            # Read in HV supply voltage and update GUI
            shared_var.voltage_monitor = sensors.hv_update(
                handle,
                labjack_io["voltage_monitor_input"],
                sensor_config["voltage_factor"],
                sensor_config["voltage_offset"],
            )
            supplyVoltage_e.delete(0, "end")
            supplyVoltage_e.insert(0, shared_var.voltage_monitor)

            # Schedule the next update
            curr_time = curr_time + update_time
            next_time = curr_time + update_time - time.monotonic()
            if next_time < 0:
                next_time = 0
            time.sleep(next_time)

        except BaseException as e:
            print("Voltage Monitor Error")
            print(e)
            break
