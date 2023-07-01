import tkinter as tk
from tkinter import ttk
from datetime import datetime  # Pulls current time from system
from tkinter.constants import FALSE
from labjack import ljm
from simple_pid import PID
import threading
import yaml
import sys
import os
import time
import traceback
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib import dates
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np

import blowercontrol
import shared_var as set
import datalogging
import voltagescan
import cpccounting
import cpcserial
import cpcfill


def my_excepthook(type):  # , value, traceback):
    # Write variables to file
    with open(time.strftime("%Y%m%d_%H%M%S") + "_error.txt", "w") as f:
        f.write("Globals:\n")
        for name in globals():
            if not name.startswith("__"):
                value = eval(name)
                f.write(f"{name} = {value}\n")
        f.write("\n")
        f.write("\nLocals:\n")
        for name, value in locals().items():
            if not name.startswith("__"):
                f.write(f"{name} = {value}\n")
        f.write("\n")
        f.write("Imported module variables:\n")
        for name in dir(set):
            if not name.startswith("__"):
                myvalue = eval(f"set.{name}")
                f.write(f"{name} = {myvalue}\n")
        f.write("\n")


# Set the excepthook
threading.excepthook = my_excepthook

#   ###################Startup####################

# Allow config file to be passed from .bat file or directly from code
if len(sys.argv) > 1:
    config_file = sys.argv[1]
else:
    config_file = "test_config.yml"

# Load config file
program_path = os.path.dirname(os.path.realpath(__file__))
with open(os.path.join(program_path, config_file), "r") as f:
    config = yaml.safe_load(f)
gui_config = config["gui_config"]

# Load Labjack
handle = ljm.openS("T7", "ANY", config["labjack"])
info = ljm.getHandleInfo(handle)
value = 10
print("Setting LJM_USB_SEND_RECEIVE_TIMEOUT_MS to %.00f milliseconds\n" % value)
LJMError = ljm.writeLibraryConfigS("LJM_USB_SEND_RECEIVE_TIMEOUT_MS", value)

# Create threading events setting flags to control other flags
stop_threads = threading.Event()
voltage_scan = threading.Event()

# Create barriers for thread control
thread_config = config["threads"]
num_threads = (
    thread_config["blower"]
    + thread_config["voltage_scan"]
    + thread_config["voltage_monitor"]
    + thread_config["datalogging"]
    + thread_config["cpc_counting"]
    + thread_config["cpc_serial"]
    + thread_config["cpc_fill"]
)
num_data_threads = thread_config["voltage_scan"] + thread_config["datalogging"]
datalog_barrier = threading.Barrier(num_data_threads)
close_barrier = threading.Barrier(num_threads + 1)


####################TKinter Button Functions####################
# Define callback function for update button in Tkinter GUI
# Voltage Cycle Button
# Switches between True and False and changes button text
def voltageCycle_callback():
    if voltage_scan.is_set() == False:
        voltage_scan.set()
        voltageCycle_b.config(text="Off")
    elif voltage_scan.is_set() == True:
        voltage_scan.clear()
        voltageCycle_b.config(text="On")


####################Main Program Functions####################
def onStart():
    # Reconfigure Start Button to Stop Button
    start_b.configure(text="Stop", command=onClose)

    # Pull in GUI settings
    set.low_dia_lim = float(lvl_e.get())
    set.high_dia_lim = float(uvl_e.get())
    set.voltage_update_time = float(voltageUpdate_e.get())
    set.size_bins = int(bins_e.get())
    set.blower_flow_set = int(blowerFlow_e.get())
    set.dia_list = dia_list_e.get().split(" ")
    set.diameter_mode = dia_option.get()

    # Configure PID Controller
    global pid
    pid_config = config["pid_config"]
    pid = PID(
        pid_config["pidp"], pid_config["pidi"], pid_config["pidd"], setpoint=set.blower_flow_set
    )
    pid.output_limits = (-0.25, 0.25)

    # Set Variables
    global control
    global labjackVoltage
    global start_time
    start_time = datetime.now()

    # Start GUI update and graphing
    update_contourf(np.array([]), np.array([]), np.array([]))
    update_gui()

    # Define threads
    global blower_thread
    blower_thread = threading.Thread(
        name="Blower Monitoring",
        target=blowercontrol.blower,
        args=(
            handle,
            config["labjack_io"],
            stop_threads,
            close_barrier,
            config["sensor_config"],
            pid,
        ),
    )
    global voltage_scan_thread
    voltage_scan_thread = threading.Thread(
        name="High Voltage",
        target=voltagescan.hv,
        args=(
            handle,
            config["labjack_io"],
            stop_threads,
            datalog_barrier,
            close_barrier,
            voltage_scan,
            config["voltage_set_config"],
        ),
    )
    global voltage_monitor_thread
    voltage_monitor_thread = threading.Thread(
        name="Voltage Monitor",
        target=voltagescan.vIn,
        args=(
            handle,
            config["labjack_io"],
            stop_threads,
            close_barrier,
            config["sensor_config"],
        ),
    )
    global data_logging_thread
    data_logging_thread = threading.Thread(
        name="Data Logging",
        target=datalogging.dataLogging,
        args=(
            stop_threads,
            datalog_barrier,
            close_barrier,
            config["dma"],
            config["data_config"],
            config["voltage_set_config"],
            file_e,
        ),
    )
    global cpc_counting_thread
    cpc_counting_thread = threading.Thread(
        name="CPC Counting",
        target=cpccounting.cpc_conc,
        args=(
            handle,
            config["labjack_io"],
            stop_threads,
            close_barrier,
            config["cpc_config"],
        ),
    )
    global cpc_serial_thread
    cpc_serial_thread = threading.Thread(
        name="Serial Read",
        target=cpcserial.serial_read,
        args=(stop_threads, close_barrier, config["data_config"]),
    )
    global cpc_fill_thread
    cpc_fill_thread = threading.Thread(
        name="CPC Fill",
        target=cpcfill.cpc_fill,
        args=(handle, config["labjack_io"], stop_threads, close_barrier),
    )
    # Start threads
    if thread_config["blower"]:
        blower_thread.start()
    if thread_config["voltage_scan"]:
        voltage_scan_thread.start()
    if thread_config["voltage_monitor"]:
        voltage_monitor_thread.start()
    if thread_config["datalogging"]:
        data_logging_thread.start()
    if thread_config["cpc_counting"]:
        cpc_counting_thread.start()
    if thread_config["cpc_serial"]:
        cpc_serial_thread.start()
    if thread_config["cpc_fill"]:
        cpc_fill_thread.start()


# Close Program
def onClose():
    # Reconfigure Stop Button to Start Button
    start_b.configure(text="Run", command=onStart)

    # Stop threads, close Labjack and Tkinter GUI
    global stopThreads
    stopThreads = True
    stop_threads.set()
    close_barrier.wait()
    ljm.close(handle)
    root.destroy()


# Program to update gui
def update_gui():
    conc_e.delete(0, "end")
    conc_e.insert(0, set.concentration)
    rh_e.delete(0, "end")
    rh_e.insert(0, "%.2f" % set.rh_read)
    flow_e.delete(0, "end")
    flow_e.insert(0, "%.2f" % set.flow_read)
    temp_e.delete(0, "end")
    temp_e.insert(0, "%.2f" % set.temp_read)
    p_e.delete(0, "end")
    p_e.insert(0, "%.2f" % set.press_read)
    dia_e.delete(0, "end")
    dia_e.insert(0, "%.2f" % set.set_diameter)
    voltageSetPoint_e.delete(0, "end")
    voltageSetPoint_e.insert(0, "%.2f" % set.ljvoltage_set_out)
    supplyVoltage_e.delete(0, "end")
    supplyVoltage_e.insert(0, "%.2f" % set.voltage_monitor)
    count_e.delete(0, "end")
    count_e.insert(0, "%.2f" % set.curr_count)
    dead_e.delete(0, "end")
    dead_e.insert(0, "%.2f" % set.pulse_width)

    root.update()
    root.after(1000, update_gui)


####################GUI Creation####################
# Creates the base canvas for TKinter
root = tk.Tk()
gui_settings = tk.Frame(root)
gui_settings.grid(row=0, column=0)

####################Tkinter Widgdets####################
# Create the TKinter widgets that allow for manual DMA Blower settings

# Heading
tk.Label(gui_settings, text=config["dma"], font=("TkDefaultFont", 12, "bold")).grid(
    row=0, column=0, columnspan=3
)

# Set Point Values Title
setpoint_title = tk.Label(
    gui_settings, text="Set Point Values", font=("TkDefaultFont", 10, "bold")
).grid(row=1, column=0, columnspan=3)

# Lower Voltage Limit
dia_list_label = tk.Label(gui_settings, text="Diameter List (nm)").grid(row=2, column=0)
dia_list_e = tk.Entry(gui_settings)
dia_list_e.insert(0, gui_config["diameter_list"])
dia_list_e.grid(row=2, column=1)

# Lower Voltage Limit
lvl_label = tk.Label(gui_settings, text="Lower Diameter Limit (nm)").grid(row=3, column=0)
lvl_e = tk.Entry(gui_settings)
lvl_e.insert(0, gui_config["low_dia_lim"])
lvl_e.grid(row=3, column=1)

# Upper Voltage Limit
uvl_label = tk.Label(gui_settings, text="Upper Diameter Limit (nm)").grid(row=4, column=0)
uvl_e = tk.Entry(gui_settings)
uvl_e.insert(0, gui_config["high_dia_lim"])
uvl_e.grid(row=4, column=1)

# Bins
bins_label = tk.Label(gui_settings, text="Interval").grid(row=5, column=0)
bins_e = tk.Entry(gui_settings)
bins_e.insert(0, gui_config["bins"])
bins_e.grid(row=5, column=1)

# Voltage Update
voltageUpdate_label = tk.Label(gui_settings, text="Interval Update Time (ms)").grid(row=6, column=0)
voltageUpdate_e = tk.Entry(gui_settings)
voltageUpdate_e.insert(0, gui_config["voltage_update_time"])
voltageUpdate_e.grid(row=6, column=1)

# Blower Flow Rate
blowerFlow_label = tk.Label(gui_settings, text="Blower Flow Rate (L/min)").grid(row=7, column=0)
blowerFlow_e = tk.Entry(gui_settings)
blowerFlow_e.insert(0, gui_config["blower_flow_set"])
blowerFlow_e.grid(row=7, column=1)

# File Location
data_storage_label = tk.Label(gui_settings, text="Data Storage (File Location)").grid(
    row=8, column=0, columnspan=3
)
file_e = tk.Entry(gui_settings, width=70)
file_e.grid(row=9, column=0, columnspan=3)

# Radiobutton
dia_option = tk.StringVar()
dia_option.set(gui_config["default_mode"])
ttk.Radiobutton(gui_settings, text="Diameter List", variable=dia_option, value="dia_list").grid(
    row=1, column=2
)
ttk.Radiobutton(gui_settings, text="Scan Interval", variable=dia_option, value="interval").grid(
    row=2, column=2
)

# Voltage Cycle Button
voltageCycle_label = tk.Label(gui_settings, text="Voltage Cycle").grid(row=4, column=2)
voltageCycle_b = tk.Button(gui_settings, text="On", command=voltageCycle_callback)
voltageCycle_b.grid(row=5, column=2)

# Start Button
start_b = tk.Button(gui_settings, text="Run", background="PaleGreen2", command=onStart)
start_b.grid(row=10, column=0, columnspan=3)

############# Graph

# Create a figure and axis for the contourf plot
graph_frame = tk.Frame(root)
graph_frame.grid(row=0, column=2)
fig = Figure(figsize=(5, 4), dpi=100)
ax = fig.add_subplot()
canvas = FigureCanvasTkAgg(fig, master=graph_frame)
canvas.get_tk_widget().pack()


cbar_min = gui_config["contour_min"]
cbar_max = gui_config["contour_max"]
cmap = "jet"
norm = colors.LogNorm(vmin=cbar_min, vmax=cbar_max)


# Create a function to update the contourf plot
def update_contourf(time_data, dp, dndlndp):
    print(set.size_bins)
    if set.graph_line:
        try:
            # Check for a new timestep
            if time_data[-1] != np.datetime64(set.graph_line[0][0]):
                if True:
                    # Check if diameters are strictly increasing
                    time_data = np.append(time_data, np.datetime64(set.graph_line[0][0]))

                    # Add new diameters to graph data
                    dp = np.vstack((dp, set.graph_line[0][2:]))

                    # Add new data to graph data
                    dndlndp = np.vstack((dndlndp, set.graph_line[1][1:]))

                    # Scroll the graph
                    if time_data.shape > (144,):
                        time_data = np.delete(time_data, 0)
                        dp = np.delete(dp, 0, 0)
                        dndlndp = np.delete(dndlndp, 0, 0)

                    # Create meshgrid for time
                    y = np.arange(0, set.size_bins - 1)
                    time1, y = np.meshgrid(time_data, y)

                    # Plot contour if there's more than one row of data
                    if time_data.shape > (1,):
                        ax.clear()
                        ax.contourf(
                            time1,
                            dp.T,
                            dndlndp.T,
                            np.arange(cbar_min, cbar_max),
                            cmap=cmap,
                            norm=norm,
                            extend="both",
                        )
                        ax.set_yscale("log")
                        ax.set_ylim(gui_config["y_min"], gui_config["y_max"])
                        ax.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))
                        ax.set_ylabel(r"Diameter [nm]", fontsize=10)

        except IndexError:
            # First line of data
            if True:
                # Add time data
                dt_array = np.empty(0, dtype="datetime64")
                time_data = np.append(dt_array, np.datetime64(set.graph_line[0][0]))

                # Add diameter data
                dp = np.asarray(set.graph_line[0][2:])

                # Add concentration data
                dndlndp = np.asarray(set.graph_line[1][1:])
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])

        except Exception:
            print(sys.exc_info()[0])
            print(sys.exc_info()[1])
            print(traceback.format_exc())
    else:
        print("No data yet")

    # Redraw the canvas
    canvas.draw()

    # Schedule the function to be called again after 1 minute
    root.after(60000, lambda: update_contourf(time_data, dp, dndlndp))


# def strictly_increasing(L):
#     return all(x < y for x, y in zip(L, L[1:]))


####################Initally Hidden Tkinter Widgets####################
monitor = tk.Frame(root)
monitor.grid(row=0, column=1)
dma_monitor = tk.Frame(monitor)
dma_monitor.grid(row=0)
flow_monitor = tk.Frame(monitor)
flow_monitor.grid(row=1)
conc_monitor = tk.Frame(monitor)
conc_monitor.grid(row=2)

tk.Label(dma_monitor, text="DMA Size Selection", font=("TkDefaultFont", 9, "bold")).grid(
    row=0, column=0, columnspan=2
)

# Current Set Voltage
voltageSetPoint_label = tk.Label(dma_monitor, text="Set Voltage").grid(row=1, column=0)
voltageSetPoint_e = tk.Entry(dma_monitor)
voltageSetPoint_e.grid(row=1, column=1)

# Current Monitor Voltage
supplyVoltage_label = tk.Label(dma_monitor, text="Supply Voltage").grid(row=2, column=0)
supplyVoltage_e = tk.Entry(dma_monitor)
supplyVoltage_e.grid(row=2, column=1)

# Define diameter label
dia_label = tk.Label(dma_monitor, text="Diameter (nm)").grid(row=3, column=0)
dia_e = tk.Entry(dma_monitor)
dia_e.grid(row=3, column=1)

tk.Label(flow_monitor, text="DMA Flow Parameters", font=("TkDefaultFont", 9, "bold")).grid(
    row=0, column=0, columnspan=2
)

# Define flow rate label
flow_label = tk.Label(flow_monitor, text="Flow sLPM").grid(row=1, column=0)
flow_e = tk.Entry(flow_monitor)
flow_e.grid(row=1, column=1)

# Define current temperature label
temp_label = tk.Label(flow_monitor, text="Temperature (C)").grid(row=2, column=0)
temp_e = tk.Entry(flow_monitor)
temp_e.grid(row=2, column=1)

# Define current RH label
rh_label = tk.Label(flow_monitor, text="Relative Humidity").grid(row=3, column=0)
rh_e = tk.Entry(flow_monitor)
rh_e.grid(row=3, column=1)

# Define current pressure label
p_label = tk.Label(flow_monitor, text="Pressure").grid(row=4, column=0)
p_e = tk.Entry(flow_monitor)
p_e.grid(row=4, column=1)

tk.Label(conc_monitor, text="CPC Pulse Counting", font=("TkDefaultFont", 9, "bold")).grid(
    row=0, column=0, columnspan=2
)

# Define cpc count label
conc_label = tk.Label(conc_monitor, text="Concentration #/cc").grid(row=1, column=0)
conc_e = tk.Entry(conc_monitor)
conc_e.grid(row=1, column=1)

# Define cpc count label
count_label = tk.Label(conc_monitor, text="Counts #").grid(row=2, column=0)
count_e = tk.Entry(conc_monitor)
count_e.grid(row=2, column=1)

# Define cpc count label
dead_label = tk.Label(conc_monitor, text="Deadtime (s)").grid(row=3, column=0)
dead_e = tk.Entry(conc_monitor)
dead_e.grid(row=3, column=1)


#############################################################
# Populate the root window with navigation buttons
root.protocol("WM_DELETE_WINDOW", onClose)
root.mainloop()
""""""
