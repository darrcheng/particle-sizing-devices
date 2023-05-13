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

import blowercontrol
import shared_var as set
import datalogging
import voltagescan
import cpccounting

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np


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


####################Startup####################

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

value = 1
print("Setting LJM_USB_SEND_RECEIVE_TIMEOUT_MS to %.00f milliseconds\n" % value)
LJMError = ljm.writeLibraryConfigS("LJM_USB_SEND_RECEIVE_TIMEOUT_MS", value)

# Create threading events setting flags to control other flags
stop_threads = threading.Event()
voltage_scan = threading.Event()
datalog_barrier = threading.Barrier(2)
close_barrier = threading.Barrier(6)


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
    update_contourf()
    update_gui()

    # # Reveal the Monitoring controls
    # voltageSetPoint_label.pack()
    # voltageSetPoint_e.pack()
    # supplyVoltage_label.pack()
    # supplyVoltage_e.pack()
    # dia_label.pack()
    # dia_e.pack()
    # conc_label.pack()
    # conc_e.pack()
    # temp_label.pack()
    # temp_e.pack()
    # rh_label.pack()
    # rh_e.pack()
    # p_label.pack()
    # p_e.pack()
    # flow_label.pack()
    # flow_e.pack()

    # Define and start threads
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
            temp_e,
            rh_e,
            p_e,
            flow_e,
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
            voltageSetPoint_e,
            dia_e,
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
            supplyVoltage_e,
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
            conc_e,
        ),
    )
    blower_thread.start()
    voltage_scan_thread.start()
    voltage_monitor_thread.start()
    data_logging_thread.start()
    cpc_counting_thread.start()


# Close Program
def onClose():
    # Reconfigure Stop Button to Start Button
    start_b.configure(text="Run", command=onStart)

    # Stop threads, close Labjack and Tkinter GUI
    global stopThreads
    stopThreads = True
    stop_threads.set()
    # time.sleep(1)
    # stop_threads.set()
    close_barrier.wait()
    # print(cpc_counting_thread.is_alive())
    ljm.close(handle)

    # time.sleep(1)
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
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib import dates

# Create a figure and axis for the contourf plot
graph_frame = tk.Frame(root)
graph_frame.grid(row=0, column=2)
fig = Figure(figsize=(5, 4), dpi=100)
ax = fig.add_subplot()
# fig, ax = plt.subplots()
canvas = FigureCanvasTkAgg(fig, master=graph_frame)
# canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
canvas.get_tk_widget().pack()
# canvas.grid(column=2)

time_data = np.array([])
dp = np.array([])
dndlndp = np.array([])

vm = 10
VM = 300
cmap = "jet"
norm = colors.LogNorm(vmin=vm, vmax=VM)


# Create a function to update the contourf plot
def update_contourf():
    if set.graph_line:
        try:
            global time_data
            if time_data[-1] != np.datetime64(set.graph_line[0][0]):
                if strictly_increasing(set.graph_line[0][2:]):
                    # check if diameters are strictly increasing
                    time_data = np.append(time_data, np.datetime64(set.graph_line[0][0]))
                    global dp
                    dp = np.vstack((dp, set.graph_line[0][2:]))
                    # dp = np.vstack((dp, [1, 2, 3]))
                    global dndlndp
                    dndlndp = np.vstack((dndlndp, set.graph_line[2][1:]))
                    # dndlndp = np.vstack((dndlndp, np.random.rand(3)))
                    y = np.arange(0, set.size_bins - 1)
                    # Scroll the graph
                    if time_data.shape > (240,):
                        time_data = np.delete(time_data, 0)
                        dp = np.delete(dp, 0, 0)
                        dndlndp = np.delete(dndlndp, 0, 0)
                    time1, y = np.meshgrid(time_data, y)
                    if time_data.shape > (1,):
                        ax.clear()
                        ax.contourf(time1, dp.T, dndlndp.T, cmap=cmap, extend="both")
                        ax.set_yscale("log")
                        ax.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))
                        ax.set_ylabel(r"Diameter [m]", fontsize=10)
                    else:
                        print("only one line of data")
                else:
                    print("not strictly increasing")
            else:
                print("not a new timestep")

        except IndexError:
            dt_array = np.empty(0, dtype="datetime64")
            time_data = np.append(dt_array, np.datetime64(set.graph_line[0][0]))
            dp = np.asarray(set.graph_line[0][2:])
            # dp = np.asarray([1, 2, 3])
            dndlndp = np.asarray(set.graph_line[2][1:])
            # dndlndp = np.asarray(np.random.rand(3))
        # print(time_data, dp, dndlndp)

        except Exception:
            print(sys.exc_info()[0])
    else:
        print("no data yet")

    # Redraw the canvas
    canvas.draw()

    # Schedule the function to be called again after 10 seconds
    root.after(60000, update_contourf)


# Call the update_contourf function to start the updating process
# update_contourf()

# Run the tkinter main loop
# root.mainloop()


def strictly_increasing(L):
    return all(x < y for x, y in zip(L, L[1:]))


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

# root.after(1000, update_gui)

#############################################################
# Populate the root window with navigation buttons
root.protocol("WM_DELETE_WINDOW", onClose)
root.mainloop()
""""""
