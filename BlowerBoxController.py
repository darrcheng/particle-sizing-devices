import tkinter as tk
from datetime import datetime  # Pulls current time from system
from tkinter.constants import FALSE
from labjack import ljm
from simple_pid import PID
import threading

# from sensors import *
import blowercontrol
import settings as settings
import datalogging
import voltagescan

####################Labjack Startup####################

handle = ljm.openS("T7", "ANY", "ANY")
info = ljm.getHandleInfo(handle)
ljm.eWriteName(handle, "AIN1_RANGE", 1.0)

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


# Lower Voltage Limit Update
def lvl_callback():
    settings.lvl = lvl_e.get()


# Upper Voltage Limit Update
def uvl_callback():
    settings.uvl = uvl_e.get()


# Step Time Update
def voltageUpdate_callback():
    settings.voltageUpdate = float(voltageUpdate_e.get())


# Number of bins Update
def bins_callback():
    settings.bins = bins_e.get()


# Blower Flow Setpoint
def blowerFlow_callback():
    settings.blowerFlow = blowerFlow_e.get()
    settings.pid.setpoint = settings.blowerFlow


# File Name Update
def file_callback():
    settings.file = file_e.get()


####################Main Program Functions####################


def onStart():
    # Reconfigure Start Button to Stop Button
    start_b.configure(text="Stop", command=onClose)

    # Configure PID Controller
    global pid
    pid = PID(settings.pidp, settings.pidi, settings.pidd, setpoint=settings.blowerFlow)
    pid.output_limits = (-0.25, 0.25)

    # Set Variables
    global control
    global labjackVoltage
    global start_time
    start_time = datetime.now()

    # Reveal the Monitoring controls
    temp_label.pack()
    temp_e.pack()
    rh_label.pack()
    rh_e.pack()
    p_label.pack()
    p_e.pack()
    flow_label.pack()
    flow_e.pack()

    # Define and start threads
    # global stop_threads
    # stop_threads = threading.Event()

    global b
    b = threading.Thread(
        name="Blower Monitoring",
        target=blowercontrol.blower,
        args=(handle, settings.labjack_io, stop_threads, pid, temp_e, rh_e, p_e, flow_e),
    )
    global v
    v = threading.Thread(
        name="High Voltage",
        target=voltagescan.hv,
        args=(handle, settings.labjack_io, stop_threads, voltage_scan, voltageSetPoint_e),
    )

    global m
    m = threading.Thread(
        name="Voltage Monitor",
        target=voltagescan.vIn,
        args=(handle, settings.labjack_io, stop_threads, supplyVoltage_e),
    )
    global l
    l = threading.Thread(
        name="Data Logging", target=datalogging.dataLogging, args=(start_time, stop_threads)
    )
    b.start()
    v.start()
    m.start()
    l.start()


# Close Program
def onClose():
    # Reconfigure Stop Button to Start Button
    start_b.configure(text="Run", command=onStart)

    # Stop threads, close Labjack and Tkinter GUI
    global stopThreads
    stopThreads = True
    stop_threads.set()
    ljm.close(handle)
    # global d
    # d.close()
    runtime.destroy()


####################GUI Creation####################
# Creates the base canvas for TKinter
runtime = tk.Tk()
gui_settings = tk.Frame(runtime)
gui_settings.pack()

####################Tkinter Widgdets####################
# Create the TKinter widgets that allow for manual DMA Blower settings

# Set Point Values Title
setpoint_title = tk.Label(gui_settings, text="Set Point Values").grid(row=0, column=3)

# Lower Voltage Limit
lvl_label = tk.Label(gui_settings, text="Lower Voltage Limit (V)").grid(row=1, column=0)
lvl_e = tk.Entry(gui_settings)
lvl_e.insert(0, settings.lvl)
lvl_b = tk.Button(gui_settings, text="Update", command=lvl_callback)
lvl_e.grid(row=1, column=1)
lvl_b.grid(row=1, column=2)

# Upper Voltage Limit
uvl_label = tk.Label(gui_settings, text="Upper Voltage Limit (V)").grid(row=1, column=4)
uvl_e = tk.Entry(gui_settings)
uvl_e.insert(0, settings.uvl)
uvl_b = tk.Button(gui_settings, text="Update", command=uvl_callback)
uvl_e.grid(row=1, column=5)
uvl_b.grid(row=1, column=6)

# Bins
bins_label = tk.Label(gui_settings, text="Bins").grid(row=2, column=0)
bins_e = tk.Entry(gui_settings)
bins_e.insert(0, settings.bins)
bins_b = tk.Button(gui_settings, text="Update", command=bins_callback)
bins_e.grid(row=2, column=1)
bins_b.grid(row=2, column=2)

# Voltage Update
voltageUpdate_label = tk.Label(gui_settings, text="Voltage Update Time (ms)").grid(row=2, column=4)
voltageUpdate_e = tk.Entry(gui_settings)
voltageUpdate_e.insert(0, settings.voltageUpdate)
voltageUpdate_b = tk.Button(gui_settings, text="Update", command=voltageUpdate_callback)
voltageUpdate_e.grid(row=2, column=5)
voltageUpdate_b.grid(row=2, column=6)

# Blower Flow Rate
blowerFlow_label = tk.Label(gui_settings, text="Blower Flow Rate (L/min)").grid(row=3, column=3)
blowerFlow_e = tk.Entry(gui_settings)
blowerFlow_e.insert(0, settings.blowerFlow)
blowerFlow_b = tk.Button(gui_settings, text="Update", command=blowerFlow_callback)
blowerFlow_e.grid(row=4, column=3)
blowerFlow_b.grid(row=4, column=4)

# File Location
data_storage_label = tk.Label(gui_settings, text="Data Storage (File Location)").grid(
    row=5, column=3
)
file_e = tk.Entry(gui_settings)
file_e.insert(0, settings.file)
file_b = tk.Button(gui_settings, text="Update", command=file_callback)
file_e.grid(row=6, column=3)
file_b.grid(row=6, column=4)

# Voltage Cycle Button
voltageCycle_label = tk.Label(gui_settings, text="Voltage Cycle").grid(row=1, column=3)
voltageCycle_b = tk.Button(gui_settings, text="On", command=voltageCycle_callback)
voltageCycle_b.grid(row=2, column=3)

# Current Set Voltage
voltageSetPoint_label = tk.Label(gui_settings, text="Set Voltage").grid(row=3, column=5)
voltageSetPoint_e = tk.Entry(gui_settings)
voltageSetPoint_e.insert(0, settings.labjackVoltage * settings.voltageFactor)
voltageSetPoint_e.grid(row=4, column=5)

# Current Monitor Voltage
supplyVoltage_label = tk.Label(gui_settings, text="Supply Voltage").grid(row=5, column=5)
supplyVoltage_e = tk.Entry(gui_settings)
supplyVoltage_e.insert(0, settings.voltageMonitor)
supplyVoltage_e.grid(row=6, column=5)

# Start Button
start_b = tk.Button(gui_settings, text="Run", command=onStart)
start_b.grid(row=9, column=3)

####################Initally Hidden Tkinter Widgets####################

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

#############################################################
# Populate the root window with navigation buttons
runtime.protocol("WM_DELETE_WINDOW", onClose)
runtime.mainloop()
""""""
