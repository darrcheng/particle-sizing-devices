from labjack import ljm
import time
from datetime import datetime  # Pulls current time from system
import numpy as np
import shared_var as shared_var
import sensors


# Controls the DMA voltage scanning
def hv(handle, labjack_io, stop_threads, voltage_scan, voltage_config, voltageSetPoint_e, dia_e):
    # Calculate voltages based on diameters
    mean_free_path = 0.0651  # um
    charge = 1.60e-19  # coloumbs
    dyn_viscosity = 1.72e-05  # kg/(m*s)
    dma_length = voltage_config["dma_length"]  # cm
    dma_outer_radius = voltage_config["dma_outer_radius"]  # cm
    dma_inner_radius = voltage_config["dma_inner_radius"]  # cm
    dma_sheath = 10000  # sccm
    if shared_var.diameter_mode == "dia_list":
        diameters = np.array(shared_var.dia_list, dtype=float)
    else:
        diameters = np.logspace(
            np.log10(shared_var.low_dia_lim),
            np.log10(shared_var.high_dia_lim),
            shared_var.size_bins,
        )
    diameters = diameters / 1000  # nm -> um
    slip_correction = 1 + 2 * mean_free_path / diameters * (
        1.257 + 0.4 * np.exp((-1.1 * diameters) / (2 * mean_free_path))
    )
    elec_mobility = (
        (charge * slip_correction) / (3 * np.pi * dyn_viscosity * diameters * 1e-6) * 1e4
    )
    set_voltages = (
        (dma_sheath / 60 * 2)
        / (4 * np.pi * dma_length * elec_mobility)
        * np.log(dma_outer_radius / dma_inner_radius)
    )
    # voltage = int(shared_var.low_dia_lim)
    # increment = shared_var.size_bins
    # labjackVoltage = voltage / voltage_config["voltage_set_factor"]
    # labjackIncrement = increment / voltage_config["voltage_set_factor"]
    # bins = (shared_var.high_dia_lim - shared_var.low_dia_lim) / shared_var.size_bins

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
                # labjackVoltage = 0

                # Loop through voltages between upper and lower limits
                for ljvoltage, curr_diameter in zip(set_voltages, diameters):
                    # Break out of loop on close
                    if stop_threads.is_set() == True:
                        print("Shutdown: Voltage Set")
                        break

                    # Stop cycle at current voltage if voltage cycle is turned off
                    if voltage_scan.is_set() == True:
                        break

                    # Set Voltage to Labjack and update GUI
                    ljm.eWriteName(
                        handle,
                        labjack_io["voltage_set_output"],
                        ljvoltage / voltage_config["voltage_set_factor"],
                    )
                    shared_var.ljvoltage_set_out = ljvoltage
                    voltageSetPoint_e.delete(0, "end")
                    voltageSetPoint_e.insert(0, shared_var.ljvoltage_set_out)

                    shared_var.set_diameter = curr_diameter * 1000
                    dia_e.delete(0, "end")
                    dia_e.insert(0, shared_var.set_diameter)

                    # Schedule the next update
                    curr_time = curr_time + update_time
                    next_time = curr_time + update_time - time.monotonic()
                    if next_time < 0:
                        next_time = 0
                    time.sleep(next_time)

                    # labjackVoltage += labjackIncrement

            # If voltage cycle is turned off, set HV supply to paused voltage
            while voltage_scan.is_set() == True:
                # Break out of loop on close
                if stop_threads.is_set() == True:
                    print("Shutdown: Voltage Set")
                    break

                # Send voltage to Labjack
                ljm.eWriteName(
                    handle,
                    labjack_io["voltage_set_output"],
                    ljvoltage / voltage_config["voltage_set_factor"],
                )

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
