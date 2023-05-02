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

import blowercontrol
import shared_var as set
import datalogging
import voltagescan
import cpccounting

####################Labjack Startup####################

if len(sys.argv) > 1:
    config_file = sys.argv[1]
else:
    config_file = "nano_config.yml"

program_path = os.path.dirname(os.path.realpath(__file__))

with open(os.path.join(program_path, config_file), "r") as f:
    config = yaml.safe_load(f)
gui_config = config["gui_config"]

handle = ljm.openS("T7", "ANY", config["labjack"])
info = ljm.getHandleInfo(handle)
# ljm.eWriteName(handle, "AIN1_RANGE", 10.0)

stop_threads = threading.Event()
voltage_scan = threading.Event()


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

    # Reveal the Monitoring controls
    voltageSetPoint_label.pack()
    voltageSetPoint_e.pack()
    supplyVoltage_label.pack()
    supplyVoltage_e.pack()
    dia_label.pack()
    dia_e.pack()
    count_label.pack()
    count_e.pack()
    temp_label.pack()
    temp_e.pack()
    rh_label.pack()
    rh_e.pack()
    p_label.pack()
    p_e.pack()
    flow_label.pack()
    flow_e.pack()

    # Define and start threads
    global blower_thread
    blower_thread = threading.Thread(
        name="Blower Monitoring",
        target=blowercontrol.blower,
        args=(
            handle,
            config["labjack_io"],
            stop_threads,
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
        args=(handle, config["labjack_io"], stop_threads, config["sensor_config"], supplyVoltage_e),
    )
    global data_logging_thread
    data_logging_thread = threading.Thread(
        name="Data Logging",
        target=datalogging.dataLogging,
        args=(start_time, stop_threads, config["dma"], file_e),
    )
    global cpc_counting_thread
    cpc_counting_thread = threading.Thread(
        name="CPC Counting",
        target=cpccounting.cpc_conc,
        args=(handle, config["labjack_io"], stop_threads, config["cpc_config"], count_e),
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
    # ljm.close(handle)
    runtime.destroy()


####################GUI Creation####################
# Creates the base canvas for TKinter
runtime = tk.Tk()
gui_settings = tk.Frame(runtime)
gui_settings.pack()

####################Tkinter Widgdets####################
# Create the TKinter widgets that allow for manual DMA Blower settings

# Heading
tk.Label(gui_settings,text = config['dma'],font= ("TkDefaultFont",12,"bold")).grid(row=0,column=0,columnspan=3)

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

####################Initally Hidden Tkinter Widgets####################

# Current Set Voltage
voltageSetPoint_label = tk.Label(runtime, text="Set Voltage")
voltageSetPoint_e = tk.Entry(runtime)

# Current Monitor Voltage
supplyVoltage_label = tk.Label(runtime, text="Supply Voltage")
supplyVoltage_e = tk.Entry(runtime)

# Define current temperature label
temp_label = tk.Label(runtime, text="Temperature (C)")
temp_e = tk.Entry(runtime)

# Define current RH label
rh_label = tk.Label(runtime, text="Relative Humidity")
rh_e = tk.Entry(runtime)

# Define current pressure label
p_label = tk.Label(runtime, text="Pressure")
p_e = tk.Entry(runtime)

# Define flow rate label
flow_label = tk.Label(runtime, text="Flow sLPM")
flow_e = tk.Entry(runtime)

# Define diameter label
dia_label = tk.Label(runtime, text="Diameter (nm)")
dia_e = tk.Entry(runtime)

# Define cpc count label
count_label = tk.Label(runtime, text="Counts #/cc")
count_e = tk.Entry(runtime)

#############################################################
# Populate the root window with navigation buttons
runtime.protocol("WM_DELETE_WINDOW", onClose)
runtime.mainloop()
""""""
