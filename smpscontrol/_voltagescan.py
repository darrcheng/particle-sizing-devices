from datetime import datetime
import numpy as np
import sensors
import sys
import threading
import time
import traceback

from labjack import ljm

import mobilitycalc

# import shared_var as shared_var


class VoltageControl:
    def __init__(
        self,
        handle,
        config,
        stop_threads,
        datalog_barrier,
        close_barrier,
        voltage_scan,
        voltmon_queue,
        voltset_queue,
    ):
        self.handle = handle
        self.config = config
        self.stop_threads = stop_threads
        self.datalog_barrier = datalog_barrier
        self.close_barrier = close_barrier
        self.voltage_scan = voltage_scan
        self.voltmon_queue = voltmon_queue
        self.voltset_queue = voltset_queue

        self.voltscan_thread = threading.Thread(target=self.set_dma_voltage)
        self.voltmon_thread = threading.Thread(target=self.read_voltage_monitor)

    def start_voltscan(self):
        self.voltscan_thread.start()

    def start_voltmon(self):
        self.voltmon_thread.start()

    # Controls the DMA voltage scanning
    def set_dma_voltage(self):
        labjack_io = self.config["labjack_io"]
        voltage_config = self.config["voltage_set_config"]
        gui_config = self.config["gui_config"]

        # Calculate voltages based on diameter list or ln spaced dimaeters
        diameters, set_voltages = self.calc_voltages(voltage_config, gui_config)

        # Constants for voltage scanning intervals
        curr_time = time.monotonic()
        update_time = 1  # seconds
        repeat_measure = int(
            gui_config["voltage_update_time"] / update_time / 1000
        )
        repeat_count = 0

        while not self.stop_threads.is_set():
            try:
                # If voltageCycle is on, cycle through voltages
                while self.voltage_scan.is_set() == False:
                    # Break out of loop on close
                    if self.stop_threads.is_set() == True:
                        print("Shutdown: Voltage Set")
                        break

                    # Set current voltage and diameter based on loop count, does not reset on error
                    ljvoltage = set_voltages[
                        int(repeat_count / repeat_measure) % len(set_voltages)
                    ]
                    curr_diameter = diameters[
                        int(repeat_count / repeat_measure) % len(set_voltages)
                    ]

                    # Hard code in a 10 kV maximum voltage for all DMAs
                    if ljvoltage > 10000:
                        ljvoltage = 10000

                    if gui_config["scan_polarity"] == "positive":
                        # Set Voltage to Labjack
                        ljm.eWriteName(
                            self.handle,
                            labjack_io["voltage_set_output_pos"],
                            ljvoltage / voltage_config["voltage_set_factor"]
                            - voltage_config["voltage_offset_calibration"],
                        )
                        ljm.eWriteName(
                            self.handle, labjack_io["voltage_set_output_neg"], 0
                        )

                    elif gui_config["scan_polarity"] == "negative":
                        # Set Voltage to Labjack
                        ljm.eWriteName(
                            self.handle,
                            labjack_io["voltage_set_output_neg"],
                            ljvoltage / voltage_config["voltage_set_factor"]
                            - voltage_config["voltage_offset_calibration"],
                        )
                        ljm.eWriteName(
                            self.handle, labjack_io["voltage_set_output_pos"], 0
                        )

                    ljvoltage_set_out = ljvoltage

                    # Update Diameter
                    set_diameter = curr_diameter

                    # Wait for datalogging
                    # self.datalog_barrier.wait()

                    # Calculate runtime
                    voltage_runtime = time.monotonic() - curr_time - update_time
                    voltset_data = {
                        "volt set thread time": datetime.now(),
                        "volt set": ljvoltage_set_out,
                        "dia set": curr_diameter,
                        "volt set runtime": voltage_runtime,
                    }
                    self.voltset_queue.put(voltset_data)

                    # Increment count number for voltage setting
                    repeat_count = repeat_count + 1

                    # Schedule the next update
                    curr_time = curr_time + update_time
                    next_time = curr_time + update_time - time.monotonic()
                    if next_time < 0:
                        next_time = 0
                        print("Slow: Voltage Set" + str(datetime.now()))
                    time.sleep(next_time)

                # If voltage cycle is turned off, set HV supply to paused voltage
                while self.voltage_scan.is_set() == True:
                    # Break out of loop on close
                    if self.stop_threads.is_set() == True:
                        print("Shutdown: Voltage Set")
                        break

                    if gui_config["scan_polarity"] == "positive":
                        # Set Voltage to Labjack
                        ljm.eWriteName(
                            self.handle,
                            labjack_io["voltage_set_output_pos"],
                            ljvoltage / voltage_config["voltage_set_factor"]
                            - voltage_config["voltage_offset_calibration"],
                        )
                        ljm.eWriteName(
                            self.handle, labjack_io["voltage_set_output_neg"], 0
                        )

                    elif gui_config["scan_polarity"] == "negative":
                        # Set Voltage to Labjack
                        ljm.eWriteName(
                            self.handle,
                            labjack_io["voltage_set_output_neg"],
                            ljvoltage / voltage_config["voltage_set_factor"]
                            - voltage_config["voltage_offset_calibration"],
                        )
                        ljm.eWriteName(
                            self.handle, labjack_io["voltage_set_output_pos"], 0
                        )

            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print("Voltage Scan" + str(ljme) + str(datetime.now()))
                time.sleep(1)

            except threading.BrokenBarrierError:
                print("Voltage Scan Barrier Broken" + str(datetime.now()))
                time.sleep(0.5)

            except BaseException as e:
                print("Voltage Scan Error")
                print(traceback.format_exc())
                self.close_barrier.wait()
                break
        print("Shutdown: Voltage Set")
        self.close_barrier.wait()

    def calc_voltages(self, voltage_config, gui_config):
        # Constants
        dma_length = voltage_config["dma_length"]  # cm
        dma_outer_radius = voltage_config["dma_outer_radius"]  # cm
        dma_inner_radius = voltage_config["dma_inner_radius"]  # cm
        dma_sheath = gui_config["blower_flow_set"] * 1000  # sccm

        # Calculate scan details from diameter list
        if gui_config["default_mode"] == "dia_list":
            diameters = np.array(gui_config["diameter_list"], dtype=float)
            # shared_var.size_bins = len(diameters)
            # shared_var.low_dia_lim = min(diameters)
            # shared_var.high_dia_lim = max(diameters)
            # shared_var.dlnDp = voltage_config["dlnDp"]

        # Calculate voltage bins using low/high limits
        else:
            diameters = np.logspace(
                np.log(gui_config["low_dia_lim"]),
                np.log(gui_config["high_dia_lim"]),
                num=gui_config["bins"],
                base=np.exp(1),
            )
            # shared_var.dlnDp = np.log(diameters[1]) - np.log(diameters[0])

        # Calculate Set Voltages from Diameters
        elec_mobility = mobilitycalc.calc_mobility_from_dia(diameters)
        set_voltages = mobilitycalc.calc_voltage_from_mobility(
            elec_mobility,
            dma_sheath,
            dma_sheath,
            dma_length,
            dma_outer_radius,
            dma_inner_radius,
        )
        print(set_voltages)
        return diameters, set_voltages

    # Define Voltage Monitor
    def read_voltage_monitor(self):
        labjack_io = self.config["labjack_io"]
        sensor_config = self.config["sensor_config"]
        gui_config = self.config["gui_config"]

        # Constants for voltage set intervals
        curr_time = time.monotonic()
        update_time = 1  # seconds

        while not self.stop_threads.is_set():
            try:
                # Read in HV supply voltage and update GUI
                voltage_monitor = sensors.hv_update(
                    self.handle,
                    labjack_io["voltage_monitor_input"],
                    sensor_config["voltage_factor"],
                    sensor_config["voltage_offset"],
                )
                if gui_config["scan_polarity"] == "positive":
                    # Set voltage monitor minimum
                    if voltage_monitor <= 0:
                        voltage_monitor = 0.001
                    else:
                        voltage_monitor = voltage_monitor
                elif gui_config["scan_polarity"] == "negative":
                    # Set voltage monitor minimum
                    if voltage_monitor >= 0:
                        voltage_monitor = -0.001
                    else:
                        voltage_monitor = voltage_monitor

                # Calculate runtime
                voltage_monitor_runtime = (
                    time.monotonic() - curr_time - update_time
                )

                volt_data = {
                    "volt monitor thread time": datetime.now(),
                    "supply_volt": voltage_monitor,
                    "volt monitor runtime": voltage_monitor_runtime,
                }
                self.voltmon_queue.put(volt_data)

                # Schedule the next update
                curr_time = curr_time + update_time
                next_time = curr_time + update_time - time.monotonic()
                if next_time < 0:
                    # if abs(next_time) / update_time > 1:
                    #     curr_time = curr_time + update_time * int(abs(next_time) / update_time)
                    next_time = 0
                    print("Slow: Voltage Monitor" + str(datetime.now()))
                time.sleep(next_time)

            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print(ljme)
                print("Voltage Monitor: " + str(ljme) + str(datetime.now()))
                time.sleep(1)

            except BaseException as e:
                print("Voltage Monitor Error")
                print(traceback.format_exc())
                break

        print("Shutdown: Voltage Monitor")
        self.close_barrier.wait()
