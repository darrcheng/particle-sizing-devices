import sys
import os
import threading
from datetime import datetime
import time
import tkinter as tk
from tkinter import ttk
import traceback
import queue

from labjack import ljm
import numpy as np
from simple_pid import PID
import yaml
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib import dates
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from _blowercontrol import BlowerControl
from _voltagescan import VoltageControl
from _datalogging import DataLogging
from _cpccounting import CPCCount

from _cpcserial import CPCSerial

from _cpcfill import CPCFill
from _datatest import DataTest

# import shared_var as shared_var


class SMPS:
    def __init__(self, root):
        ##### Inital Program Setup ############################################
        # Allow config file to be passed from .bat file or directly from code
        if len(sys.argv) > 1:
            self.config_file = sys.argv[1]
        else:
            self.config_file = "..\\long_config.yml"

        # Load config file
        self.program_path = os.path.dirname(os.path.realpath(__file__))
        with open(os.path.join(self.program_path, self.config_file), "r") as f:
            self.config = yaml.safe_load(f)
        gui_config = self.config["gui_config"]

        ##### Load Labjack
        self.handle = ljm.openS("T7", "ANY", self.config["labjack"])
        info = ljm.getHandleInfo(self.handle)
        value = 10
        print(
            "Setting LJM_USB_SEND_RECEIVE_TIMEOUT_MS to %.00f milliseconds\n"
            % value
        )
        LJMError = ljm.writeLibraryConfigS(
            "LJM_USB_SEND_RECEIVE_TIMEOUT_MS", value
        )

        self.all_data = {}
        self.file_dir = None

        ##### Threading related initalizations ################################
        # Create threading events to control on/off
        self.stop_threads = threading.Event()
        self.voltage_scan = threading.Event()
        self.blower_queue = queue.Queue()
        self.voltmon_queue = queue.Queue()
        self.voltset_queue = queue.Queue()
        self.count_queue = queue.Queue()
        self.serial_queue = queue.Queue()
        self.fill_queue = queue.Queue(maxsize=5)
        self.graph_queue = queue.Queue()

        # Create barriers for thread control
        self.thread_config = self.config["threads"]
        num_data_threads = (
            self.thread_config["voltage_scan"]
            + self.thread_config["datalogging"]
        )
        num_threads = (
            self.thread_config["blower"]
            + self.thread_config["voltage_scan"]
            + self.thread_config["voltage_monitor"]
            + self.thread_config["datalogging"]
            + self.thread_config["cpc_counting"]
            + self.thread_config["cpc_serial"]
            + self.thread_config["cpc_fill"]
        )
        self.datalog_barrier = threading.Event()
        self.close_barrier = threading.Barrier(num_threads + 1)

        # Import class methods
        self.blower_control = BlowerControl(
            self.handle,
            self.config,
            self.stop_threads,
            self.close_barrier,
            self.blower_queue,
        )
        self.voltage_control = VoltageControl(
            self.handle,
            self.config,
            self.stop_threads,
            self.datalog_barrier,
            self.close_barrier,
            self.voltage_scan,
            self.voltmon_queue,
            self.voltset_queue,
        )
        self.cpc_count = CPCCount(
            self.handle,
            self.config,
            self.stop_threads,
            self.close_barrier,
            self.count_queue,
        )
        self.cpc_serial = CPCSerial(
            self.config,
            self.stop_threads,
            self.close_barrier,
            self.serial_queue,
            self.fill_queue,
        )
        self.cpc_fill = CPCFill(
            self.handle,
            self.config,
            self.stop_threads,
            self.close_barrier,
            self.fill_queue,
        )
        self.data_test = DataTest(self.all_data)

        # Data Queue Dict Keys
        key_config = self.config["keys"]
        self.blower_keys = key_config["blower"]
        self.voltset_keys = key_config["voltage_scan"]
        self.voltmon_keys = key_config["voltage_monitor"]
        self.count_keys = key_config["cpc_counting"]
        self.serial_keys = key_config["cpc_serial"]

        ##### GUI Setup ########################################################
        ##### SMPS Settings Input #####
        self.set_frame = tk.Frame(root)
        self.set_frame.grid(row=0, column=0)
        # Heading
        tk.Label(
            self.set_frame,
            text=self.config["dma"],
            font=("TkDefaultFont", 12, "bold"),
        ).grid(row=0, column=0, columnspan=3)

        # Set Point Values Title
        setpoint_title = tk.Label(
            self.set_frame,
            text="Set Point Values",
            font=("TkDefaultFont", 10, "bold"),
        ).grid(row=1, column=0, columnspan=3)

        # Lower Voltage Limit
        dia_list_label = tk.Label(
            self.set_frame, text="Diameter List (nm)"
        ).grid(row=2, column=0)
        self.dia_list_e = tk.Entry(self.set_frame)
        self.dia_list_e.insert(0, gui_config["diameter_list"])
        self.dia_list_e.grid(row=2, column=1)

        # Lower Voltage Limit
        lvl_label = tk.Label(
            self.set_frame, text="Lower Diameter Limit (nm)"
        ).grid(row=3, column=0)
        self.low_dia_e = tk.Entry(self.set_frame)
        self.low_dia_e.insert(0, gui_config["low_dia_lim"])
        self.low_dia_e.grid(row=3, column=1)

        # Upper Voltage Limit
        uvl_label = tk.Label(
            self.set_frame, text="Upper Diameter Limit (nm)"
        ).grid(row=4, column=0)
        self.high_dia_e = tk.Entry(self.set_frame)
        self.high_dia_e.insert(0, gui_config["high_dia_lim"])
        self.high_dia_e.grid(row=4, column=1)

        # Bins
        bins_label = tk.Label(self.set_frame, text="Interval").grid(
            row=5, column=0
        )
        self.bins_e = tk.Entry(self.set_frame)
        self.bins_e.insert(0, gui_config["bins"])
        self.bins_e.grid(row=5, column=1)

        # Voltage Update
        voltageUpdate_label = tk.Label(
            self.set_frame, text="Interval Update Time (ms)"
        ).grid(row=6, column=0)
        self.sample_int_e = tk.Entry(self.set_frame)
        self.sample_int_e.insert(0, gui_config["voltage_update_time"])
        self.sample_int_e.grid(row=6, column=1)

        # Blower Flow Rate
        blowerFlow_label = tk.Label(
            self.set_frame, text="Blower Flow Rate (L/min)"
        ).grid(row=7, column=0)
        self.blower_flow_e = tk.Entry(self.set_frame)
        self.blower_flow_e.insert(0, gui_config["blower_flow_set"])
        self.blower_flow_e.grid(row=7, column=1)

        # File Location
        data_storage_label = tk.Label(
            self.set_frame, text="Data Storage (File Location)"
        ).grid(row=8, column=0, columnspan=3)
        self.file_dir_e = tk.Entry(self.set_frame, width=70)
        self.file_dir_e.grid(row=9, column=0, columnspan=3)

        # Scan Mode
        self.dia_opt_b = tk.StringVar()
        self.dia_opt_b.set(gui_config["default_mode"])
        ttk.Radiobutton(
            self.set_frame,
            text="Diameter List",
            variable=self.dia_opt_b,
            value="dia_list",
        ).grid(row=2, column=2)
        ttk.Radiobutton(
            self.set_frame,
            text="Scan Interval",
            variable=self.dia_opt_b,
            value="interval",
        ).grid(row=3, column=2)

        # Scan Polarity
        self.polarity_b = tk.StringVar()
        self.polarity_b.set(gui_config["scan_polarity"])
        ttk.Radiobutton(
            self.set_frame,
            text="Positive",
            variable=self.polarity_b,
            value="positive",
        ).grid(row=4, column=2)
        ttk.Radiobutton(
            self.set_frame,
            text="Negative",
            variable=self.polarity_b,
            value="negative",
        ).grid(row=5, column=2)

        # Voltage Cycle Button
        voltageCycle_label = tk.Label(
            self.set_frame, text="Voltage Cycle"
        ).grid(row=6, column=2)
        self.volt_on_b = tk.Button(
            self.set_frame, text="On", command=self.voltageCycle_callback
        )
        self.volt_on_b.grid(row=7, column=2)

        # Start Button
        self.start_b = tk.Button(
            self.set_frame,
            text="Run",
            background="PaleGreen2",
            command=self.onStart,
        )
        self.start_b.grid(row=10, column=0, columnspan=3)

        ##### Parameter Monitor #####
        self.monitor = tk.Frame(root)
        self.monitor.grid(row=0, column=1)
        self.dma_monitor = tk.Frame(self.monitor)
        self.dma_monitor.grid(row=0)
        self.flow_monitor = tk.Frame(self.monitor)
        self.flow_monitor.grid(row=1)
        self.conc_monitor = tk.Frame(self.monitor)
        self.conc_monitor.grid(row=2)

        tk.Label(
            self.dma_monitor,
            text="DMA Size Selection",
            font=("TkDefaultFont", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2)

        # Current Set Voltage
        voltageSetPoint_label = tk.Label(
            self.dma_monitor, text="Set Voltage"
        ).grid(row=1, column=0)
        self.set_volt_e = tk.Entry(self.dma_monitor)
        self.set_volt_e.grid(row=1, column=1)

        # Current Monitor Voltage
        supplyVoltage_label = tk.Label(
            self.dma_monitor, text="Supply Voltage"
        ).grid(row=2, column=0)
        self.act_volt_e = tk.Entry(self.dma_monitor)
        self.act_volt_e.grid(row=2, column=1)

        # Define diameter label
        dia_label = tk.Label(self.dma_monitor, text="Diameter (nm)").grid(
            row=3, column=0
        )
        self.set_dia_e = tk.Entry(self.dma_monitor)
        self.set_dia_e.grid(row=3, column=1)

        tk.Label(
            self.flow_monitor,
            text="DMA Flow Parameters",
            font=("TkDefaultFont", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2)

        # Define flow rate label
        flow_label = tk.Label(self.flow_monitor, text="Flow sLPM").grid(
            row=1, column=0
        )
        self.act_flow_e = tk.Entry(self.flow_monitor)
        self.act_flow_e.grid(row=1, column=1)

        # Define current temperature label
        temp_label = tk.Label(self.flow_monitor, text="Temperature (C)").grid(
            row=2, column=0
        )
        self.act_temp_e = tk.Entry(self.flow_monitor)
        self.act_temp_e.grid(row=2, column=1)

        # Define current RH label
        rh_label = tk.Label(self.flow_monitor, text="Relative Humidity").grid(
            row=3, column=0
        )
        self.act_rh_e = tk.Entry(self.flow_monitor)
        self.act_rh_e.grid(row=3, column=1)

        # Define current pressure label
        p_label = tk.Label(self.flow_monitor, text="Pressure").grid(
            row=4, column=0
        )
        self.act_p_e = tk.Entry(self.flow_monitor)
        self.act_p_e.grid(row=4, column=1)

        tk.Label(
            self.conc_monitor,
            text="CPC Pulse Counting",
            font=("TkDefaultFont", 9, "bold"),
        ).grid(row=0, column=0, columnspan=2)

        # Define cpc count label
        conc_label = tk.Label(
            self.conc_monitor, text="Concentration #/cc"
        ).grid(row=1, column=0)
        self.act_conc_e = tk.Entry(self.conc_monitor)
        self.act_conc_e.grid(row=1, column=1)

        # Define cpc count label
        count_label = tk.Label(self.conc_monitor, text="Counts #").grid(
            row=2, column=0
        )
        self.act_count_e = tk.Entry(self.conc_monitor)
        self.act_count_e.grid(row=2, column=1)

        # Define cpc count label
        dead_label = tk.Label(self.conc_monitor, text="Deadtime (s)").grid(
            row=3, column=0
        )
        self.act_dead_e = tk.Entry(self.conc_monitor)
        self.act_dead_e.grid(row=3, column=1)

        ############# Graph

        # Create a figure and axis for the contourf plot
        self.graph_frame = tk.Frame(root)
        self.graph_frame.grid(row=0, column=2)
        fig = Figure(figsize=(5, 4), dpi=100)
        self.ax = fig.add_subplot()
        self.canvas = FigureCanvasTkAgg(fig, master=self.graph_frame)
        self.canvas.get_tk_widget().pack()

    ##### Main Program Functions ##############################################
    def onStart(self):
        # Reconfigure Start Button to Stop Button
        self.start_b.configure(text="Stop", command=self.onClose)

        # Pull in GUI settings
        new_set = {}
        new_set["low_dia_lim"] = float(self.low_dia_e.get())
        new_set["high_dia_lim"] = float(self.high_dia_e.get())
        new_set["voltage_update_time"] = float(self.sample_int_e.get())
        new_set["bins"] = int(self.bins_e.get())
        new_set["blower_flow_set"] = int(self.blower_flow_e.get())
        new_set["diameter_list"] = self.dia_list_e.get().split(" ")
        new_set["default_mode"] = self.dia_opt_b.get()
        new_set["scan_polarity"] = self.polarity_b.get()

        # Update the config file
        for key in new_set:
            self.config["gui_config"][key] = new_set[key]

        # Configure PID Controller
        global pid
        pid_config = self.config["pid_config"]
        pid = PID(
            pid_config["pidp"],
            pid_config["pidi"],
            pid_config["pidd"],
            setpoint=self.config["gui_config"]["blower_flow_set"],
        )
        pid.output_limits = (-0.25, 0.25)

        if self.thread_config["blower"]:
            self.blower_control.set_pid(pid)
            self.blower_control.start()
        if self.thread_config["voltage_scan"]:
            self.voltage_control.start_voltscan()
        if self.thread_config["voltage_monitor"]:
            self.voltage_control.start_voltmon()
        if self.thread_config["cpc_counting"]:
            self.cpc_count.start()
        if self.thread_config["cpc_serial"]:
            self.cpc_serial.start()
        if self.thread_config["cpc_fill"]:
            self.cpc_fill.start()

        self.data_logging = DataLogging(
            self.config,
            self.stop_threads,
            self.datalog_barrier,
            self.close_barrier,
            self.file_dir_e,
            self.all_data,
            self.graph_queue
        )
        # global data_logging_thread
        self.data_logging_thread = threading.Thread(
            name="Data Logging",
            target=self.data_logging.data_logging,
            args=(),
        )

        self.data_logging_thread.start()

        # Start GUI update and graphing
        self.curr_time = False
        self.read_thread_data()
        self.update_contourf(np.array([]), np.array([]), np.array([]))
        self.update_gui()

    def pause_for_even_time(self):
        """Pauses program until an even time interval is reached
        ie: If interval is 5 min program starts at 12:33, pause until 12:35"""
        interval = self.config["start_interval"]
        current_time = time.localtime()
        current_minute = current_time.tm_min
        current_seconds = current_time.tm_sec

        # Calculate the number of minutes remaining until the next 10-minute interval
        minutes_remaining = (interval - current_minute % interval) % interval

        # Calculate the total time in seconds to sleep until the next interval
        total_seconds_to_sleep = minutes_remaining * 60 - current_seconds
        if total_seconds_to_sleep < 0:
            total_seconds_to_sleep = interval * 60 + total_seconds_to_sleep

        # Print the time when the code will start
        start_time = time.strftime(
            "%H:%M:%S", time.localtime(time.time() + total_seconds_to_sleep)
        )
        dma = self.config["dma"]
        print(f"{dma} will start at: {start_time}")

        # Wait until the next 10-minute interval
        time.sleep(total_seconds_to_sleep)

    # Close Program
    def onClose(self):
        # Reconfigure Stop Button to Start Button
        self.start_b.configure(text="Run", command=self.onStart)

        # Stop threads, close Labjack and Tkinter GUI
        global stopThreads
        stopThreads = True
        self.stop_threads.set()
        self.close_barrier.wait()
        ljm.close(self.handle)
        root.destroy()

    def voltageCycle_callback(self):
        if self.voltage_scan.is_set() == False:
            self.voltage_scan.set()
            self.volt_on_b.config(text="Off")
        elif self.voltage_scan.is_set() == True:
            self.voltage_scan.clear()
            self.volt_on_b.config(text="On")

    def read_thread_data(self):
        self.read_update_time = 1
        try:
            try:
                self.blower_data = self.blower_queue.get_nowait()
            except queue.Empty:
                self.blower_data = dict.fromkeys(self.blower_keys, np.nan)
            try:
                self.voltset_data = self.voltset_queue.get_nowait()
            except queue.Empty:
                self.voltset_data = dict.fromkeys(self.voltset_keys, np.nan)
            try:
                self.voltmon_data = self.voltmon_queue.get_nowait()
            except queue.Empty:
                self.voltmon_data = dict.fromkeys(self.voltmon_keys, np.nan)
            try:
                self.count_data = self.count_queue.get_nowait()
            except queue.Empty:
                self.count_data = dict.fromkeys(self.count_keys, np.nan)
            try:
                self.serial_data = self.serial_queue.get_nowait()
            except queue.Empty:
                self.serial_data = dict.fromkeys(self.serial_keys, np.nan)
            self.all_data["blower"] = self.blower_data
            self.all_data["voltset"] = self.voltset_data
            self.all_data["voltmon"] = self.voltmon_data
            self.all_data["count"] = self.count_data
            self.all_data["serial"] = self.serial_data
            # print(self.all_data)
            self.datalog_barrier.set()
        except Exception:
            print(traceback.format_exc())

        # Schedule the next update
        if not self.curr_time:
            self.curr_time = time.monotonic()
            print(self.curr_time)
        else:
            self.curr_time = self.curr_time + self.read_update_time
        next_time = self.curr_time + self.read_update_time - time.monotonic()

        root.after(int(next_time * 1000), self.read_thread_data)

    # Program to update gui
    def update_gui(self):
        try:
            self.act_rh_e.delete(0, "end")
            self.act_rh_e.insert(0, "%.2f" % self.blower_data["rh"])
            self.act_flow_e.delete(0, "end")
            self.act_flow_e.insert(0, "%.2f" % self.blower_data["flow"])
            self.act_temp_e.delete(0, "end")
            self.act_temp_e.insert(0, "%.2f" % self.blower_data["temp"])
            self.act_p_e.delete(0, "end")
            self.act_p_e.insert(0, "%.2f" % self.blower_data["press"])
        except:
            print("No Blower Monitor Data")
        try:
            self.act_volt_e.delete(0, "end")
            self.act_volt_e.insert(0, "%.2f" % self.voltmon_data["supply_volt"])
        except:
            print("No Voltage Monitor Data")
        try:
            self.set_dia_e.delete(0, "end")
            self.set_dia_e.insert(0, "%.2f" % self.voltset_data["dia set"])
            self.set_volt_e.delete(0, "end")
            self.set_volt_e.insert(0, "%.2f" % self.voltset_data["volt set"])
        except:
            print("No Voltage Set Data")
        try:
            self.act_conc_e.delete(0, "end")
            self.act_conc_e.insert(0, self.count_data["concentration"])
            self.act_count_e.delete(0, "end")
            self.act_count_e.insert(0, "%.2f" % self.count_data["count"])
            self.act_dead_e.delete(0, "end")
            self.act_dead_e.insert(0, "%.2f" % self.count_data["pulse width"])
        except:
            print("No CPC Count Data")
        # self.data_test.print_data()
        root.update()
        root.after(1000, self.update_gui)

    # Create a function to update the contourf plot
    def update_contourf(self, time_data, dp, dndlndp):
        # print(set.size_bins)
        gui_config = self.config["gui_config"]
        cbar_min = gui_config["contour_min"]
        cbar_max = gui_config["contour_max"]
        cmap = "jet"
        norm = colors.LogNorm(vmin=cbar_min, vmax=cbar_max)
        graph_line = self.data_logging.share_graph_data()
        if graph_line:
            try:
                # Check for a new timestep
                if time_data[-1] != np.datetime64(graph_line[0][0]):
                    if True:
                        # Check if diameters are strictly increasing
                        time_data = np.append(
                            time_data,
                            np.datetime64(graph_line[0][0]),
                        )

                        # Add new diameters to graph data
                        dp = np.vstack((dp, graph_line[1][1:]))

                        # Add new data to graph data
                        dndlndp = np.vstack((dndlndp, graph_line[2][1:]))

                        # Scroll the graph
                        if time_data.shape > (144,):
                            time_data = np.delete(time_data, 0)
                            dp = np.delete(dp, 0, 0)
                            dndlndp = np.delete(dndlndp, 0, 0)

                        # Create meshgrid for time
                        y = np.arange(0, len(graph_line[1][1:]))
                        time1, y = np.meshgrid(time_data, y)

                        # Plot contour if there's more than one row of data
                        if time_data.shape > (1,):
                            self.ax.clear()
                            self.ax.contourf(
                                time1,
                                dp.T,
                                dndlndp.T,
                                np.arange(cbar_min, cbar_max),
                                cmap=cmap,
                                norm=norm,
                                extend="both",
                            )
                            self.ax.set_yscale("log")
                            self.ax.set_ylim(
                                gui_config["y_min"], gui_config["y_max"]
                            )
                            self.ax.xaxis.set_major_formatter(
                                dates.DateFormatter("%H:%M")
                            )
                            self.ax.set_ylabel(r"Diameter [nm]", fontsize=10)

            except IndexError:
                # First line of data
                if True:
                    # Add time data
                    dt_array = np.empty(0, dtype="datetime64")
                    time_data = np.append(
                        dt_array, np.datetime64(graph_line[0][0])
                    )

                    # Add diameter data
                    dp = np.asarray(graph_line[1][1:])

                    # Add concentration data
                    dndlndp = np.asarray(graph_line[2][1:])
                print(sys.exc_info()[0])
                print(sys.exc_info()[1])

            except Exception:
                print(sys.exc_info()[0])
                print(sys.exc_info()[1])
                print(traceback.format_exc())
        else:
            print("No data yet")

        # Redraw the canvas
        self.canvas.draw()

        # Schedule the function to be called again after 1 minute
        root.after(60000, lambda: self.update_contourf(time_data, dp, dndlndp))


if __name__ == "__main__":
    root = tk.Tk()
    root.title("Instrument GUI")
    app = SMPS(root)  # , "test_config.yml")
    root.mainloop()
