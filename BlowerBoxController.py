import tkinter as tk
import csv
import time
from datetime import datetime  # Pulls current time from system
from tkinter.constants import FALSE
from labjack import ljm
from simple_pid import PID
import threading

from sensors import *
import blowercontrol

####################Labjack Startup####################

handle = ljm.openS("T7", "ANY", "ANY")
info = ljm.getHandleInfo(handle)
ljm.eWriteName(handle, "AIN1_RANGE", 1.0)

####################Default Variable Settings####################
# General Settings
file = "C:\\Users\\Jen Lab\\Blower_Box\\trialrun.csv"  # File Name
stopThreads = False  # Bool to help close program
timer = 0

# Flow Settings
pidp = 0.2  # PID Proportional Gain
pidi = 0  # PID Integral Gain
pidd = 0  # PID Derivative Gain
control = 0  # PID Output
blowerFlow = 15  # Set Blower Flow Rate in [LPM]

# Flow Measurement Variables
measured = 0  # Measured flow rate
rhRead = 0  # Measured relative humidity
tempRead = 0  # Measured temperature
pRead = 0  # Measured pressure

# Voltage Cycle Settings
voltageCycle = True  # Turn voltage cycling on and off
lvl = 10  # Lower Voltage Limit #V will be 100
uvl = 200  # Upper Voltage Limit #V will be 8000'
bins = 10  # Number of steps in voltage cycle
voltageUpdate = 5000  # Time between each voltage step
labjackVoltage = 0  # Labjack output to control HV supply
voltageMonitor = 0  # Current voltage read from HV supply monitor
voltageFactor = 10000 / 5  # Scaling for HV Supply

# Initalizing threads for running blower and voltage setting codes
b = None  # Bloewr Control
v = None  # Voltage Set
m = None  # Voltage Monitor

# # Labjack Inputs
flow_read_input = "AIN0"
voltage_monitor_input = "AIN1"
press_input = "AIN2"
temp_input = "AIN3"
rh_input = "AIN4"
voltage_set_ouput = "DAC0"
flow_set_output = "TDAC0"

labjack_io = {
    "flow_read_input": "AIN0",
    "voltage_monitor_input": "AIN1",
    "press_input": "AIN2",
    "temp_input": "AIN3",
    "rh_input": "AIN4",
    "voltage_set_output": "DAC0",
    "flow_set_output": "TDAC0",
}


####################TKinter Button Functions####################
# Define callback function for update button in Tkinter GUI
# Voltage Cycle Button
# Switches between True and False and changes button text
def voltageCycle_callback():
    global voltageCycle
    voltageCycle = not voltageCycle
    if voltageCycle == True:
        voltageCycle_b.config(text="On")
    if voltageCycle == False:
        voltageCycle_b.config(text="Off")
    print(voltageCycle)


# Lower Voltage Limit Update
def lvl_callback():
    global lvl
    lvl = lvl_e.get()


# Upper Voltage Limit Update
def uvl_callback():
    global uvl
    uvl = uvl_e.get()


# Step Time Update
def voltageUpdate_callback():
    global voltageUpdate
    voltageUpdate = float(voltageUpdate_e.get())


# Number of bins Update
def bins_callback():
    global bins
    bins = bins_e.get()


# Blower Flow Setpoint
def blowerFlow_callback():
    global blowerFlow
    blowerFlow = blowerFlow_e.get()
    pid.setpoint = blowerFlow


# File Name Update
def file_callback():
    global file
    file = file_e.get()


####################Main Program Functions####################


def onStart():
    # Reconfigure Start Button to Stop Button
    start_b.configure(text="Stop", command=onClose)

    # Configure PID Controller
    global pid
    pid = PID(pidp, pidi, pidd, setpoint=blowerFlow)
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

    # # Controls the blower with PID code to ensure the flow rate stays at the specified flow rate
    # def blower():
    #     global tempRead
    #     global rhRead
    #     global pRead
    #     global measured

    #     # Set flow to 0 LPM and pause to allow blower to slow down
    #     # tdac_flow.update(0,0)
    #     ljm.eWriteName(handle, flow_set_output, 0)
    #     time.sleep(5)

    #     # Constants for flow intervals
    #     flow_time = datetime.now()
    #     flow_count = 0
    #     flow_update_time = 200  # milliseconds

    #     # Infinite Loop
    #     while True:
    #         try:
    #             # Break out of loop on close
    #             if stopThreads == True:
    #                 print("Shutdown: Sheath Flow Sensors")
    #                 break

    #             # Pause until time to start next iteration
    #             flow_milliseconds = 0
    #             while flow_milliseconds < flow_update_time:
    #                 flow_time_new = datetime.now()
    #                 flow_milliseconds = (
    #                     int((flow_time_new - flow_time).total_seconds() * 1000)
    #                     - flow_count * flow_update_time
    #                 )
    #                 time.sleep(0.001)
    #             flow_count += 1

    #             # Read temperature and update GUI
    #             tempRead = temp_update(handle, temp_input)
    #             temp_e.delete(0, "end")
    #             temp_e.insert(0, tempRead)

    #             # Read RH, correct for temperature and update GUI
    #             rhRead = rh_update(handle, rh_input) / (1.0546 - 0.00216 * tempRead)
    #             rh_e.delete(0, "end")
    #             rh_e.insert(0, rhRead)

    #             # Read Pressure and update GUI
    #             pRead = press_update(handle, press_input)
    #             p_e.delete(0, "end")
    #             p_e.insert(0, pRead)

    #             # Read Flow Rate and update GUI
    #             flowRead = flow_update(handle, flow_read_input)
    #             flow_e.delete(0, "end")
    #             flow_e.insert(0, flowRead)

    #             # PID Function
    #             measured = flow_update(handle, flow_read_input)
    #             control = 0.016 * blowerFlow + 1.8885 + pid(measured)

    #             # Set blower voltage
    #             ljm.eWriteName(handle, flow_set_output, control)

    #         except BaseException:
    #             print("Sheath Flow Sensor Error")
    #             break

    # Controls the DMA voltage scanning
    def hv():
        global lvl  # lower voltage limit
        global uvl  # upper voltage limit
        global bins
        global voltageUpdate
        global labjackVoltage

        # Set variables based on GUI inputs
        voltage = int(lvl)
        increment = (int(uvl) - int(lvl)) / int(bins)
        print(increment)
        labjackVoltage = voltage / voltageFactor
        labjackIncrement = increment / voltageFactor

        while True:
            try:
                # Break out of loop on close
                if stopThreads == True:
                    print(2)
                    break

                # If voltageCycle is on, cycle through voltages
                while voltageCycle == True:
                    # Break out of loop on close
                    if stopThreads == True:
                        print(3)
                        break

                    # Constants for voltage intervals
                    voltage_time = datetime.now()
                    voltage_count = 0

                    # Reset Labjack Voltage
                    labjackVoltage = 0

                    # Loop through voltages between upper and lower limits
                    for i in range(int(bins)):
                        # Break out of loop on close
                        if stopThreads == True:
                            print(4)
                            break

                        # Stop cycle at current voltage if voltage cycle is turned off
                        if voltageCycle == False:
                            break

                        # Set Voltage to Labjack and update GUI
                        # dac1_val = d.voltageToDACBits(labjackVoltage)
                        # d.getFeedback(u3.DAC1_8(dac1_val))
                        # tdac_voltage.update(labjackVoltage,0)
                        ljm.eWriteName(handle, voltage_set_ouput, labjackVoltage)
                        print(labjackVoltage)
                        voltageSetPoint_e.delete(0, "end")
                        voltageSetPoint_e.insert(0, labjackVoltage * voltageFactor)

                        # Pause for time specified in GUI
                        voltage_milliseconds = 0
                        while voltage_milliseconds < voltageUpdate:
                            voltage_time_new = datetime.now()
                            voltage_milliseconds = (
                                int((voltage_time_new - voltage_time).total_seconds() * 1000)
                                - voltage_count * voltageUpdate
                            )
                            time.sleep(0.001)
                        voltage_count += 1
                        print(voltage_milliseconds)

                        labjackVoltage += labjackIncrement

                # If voltage cycle is turned off, set HV supply to paused voltage
                while voltageCycle == False:
                    # Break out of loop on close
                    if stopThreads == True:
                        print(3)
                        break

                    # Send voltage to Labjack
                    # dac1_val = d.voltageToDACBits(labjackVoltage)
                    # d.getFeedback(u3.DAC1_8(dac1_val))
                    ljm.eWriteName(handle, voltage_set_ouput, labjackVoltage)

            except BaseException:
                print(9)
                break

    # Define Voltage Monitor
    def vIn():
        global voltageMonitor

        # Constants for voltage monitoring intervals
        monitor_time = datetime.now()
        monitor_count = 0

        while True:
            try:
                # Break out of loop on program close
                if stopThreads == True:
                    print(5)
                    break

                # Pause for 0.2 seconds
                monitor_milliseconds = 0
                while monitor_milliseconds < 200:
                    monitor_time_new = datetime.now()
                    monitor_milliseconds = (
                        int((monitor_time_new - monitor_time).total_seconds() * 1000)
                        - monitor_count * 200
                    )
                    time.sleep(0.001)
                monitor_count += 1

                # Read in HV supply voltage and update GUI
                voltageMonitor = hv_update(handle, voltage_monitor_input)
                supplyVoltage_e.delete(0, "end")
                supplyVoltage_e.insert(0, voltageMonitor)

            except BaseException as e:
                print(e)
                break

    def dataLogging():
        # Open CSV logging file
        with open(file, mode="w", newline="") as data_file:
            data_writer = csv.writer(data_file, delimiter=",")
            data_writer.writerow(
                [
                    "Count",
                    "Timer",
                    "Elapsed Time",
                    "Flow Rate [LPM]",
                    "Set Voltage [V]",
                    "Actual Voltage[V]",
                    "Temperature [C]",
                    "RH[%]",
                    "Pressure[kPa]",
                ]
            )

            log_time = start_time
            log_elapsed = 0
            count = 0
            # Infinite Loop
            while True:
                try:
                    # Break out of loop on program close
                    if stopThreads == True:
                        print(6)
                        break

                    # Pause until next date time increment is reached
                    log_milliseconds = 0
                    while log_milliseconds < 500:
                        log_time_new = datetime.now()
                        log_milliseconds = (
                            int((log_time_new - start_time).total_seconds() * 1000) - count * 500
                        )
                        time.sleep(0.05)
                    log_elapsed += float((log_time_new - log_time).total_seconds())
                    count += 1
                    log_time = log_time_new

                    # Write Data to CSV file
                    data_writer.writerow(
                        [
                            count,
                            log_time,
                            log_elapsed,
                            measured,
                            labjackVoltage * voltageFactor,
                            voltageMonitor,
                            tempRead,
                            rhRead,
                            pRead,
                        ]
                    )

                except BaseException:
                    print(9)
                    break

    # Define and start threads
    stop_threads = threading.Event()
    stop_scan = threading.Event()
    global b
    b = threading.Thread(
        name="Blower Monitoring",
        target=blowercontrol.blower,
        args=(handle, labjack_io, stopThreads, pid, temp_e, rh_e, p_e, flow_e, blowerFlow),
    )
    global v
    v = threading.Thread(name="High Voltage", target=hv)
    global m
    m = threading.Thread(name="Voltage Monitor", target=vIn)
    global l
    l = threading.Thread(name="Data Logging", target=dataLogging)
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
    ljm.close(handle)
    # global d
    # d.close()
    runtime.destroy()


####################GUI Creation####################
# Creates the base canvas for TKinter
runtime = tk.Tk()
settings = tk.Frame(runtime)
settings.pack()

####################Tkinter Widgdets####################
# Create the TKinter widgets that allow for manual DMA Blower settings

# Set Point Values Title
setpoint_title = tk.Label(settings, text="Set Point Values").grid(row=0, column=3)

# Lower Voltage Limit
lvl_label = tk.Label(settings, text="Lower Voltage Limit (V)").grid(row=1, column=0)
lvl_e = tk.Entry(settings)
lvl_e.insert(0, lvl)
lvl_b = tk.Button(settings, text="Update", command=lvl_callback)
lvl_e.grid(row=1, column=1)
lvl_b.grid(row=1, column=2)

# Upper Voltage Limit
uvl_label = tk.Label(settings, text="Upper Voltage Limit (V)").grid(row=1, column=4)
uvl_e = tk.Entry(settings)
uvl_e.insert(0, uvl)
uvl_b = tk.Button(settings, text="Update", command=uvl_callback)
uvl_e.grid(row=1, column=5)
uvl_b.grid(row=1, column=6)

# Bins
bins_label = tk.Label(settings, text="Bins").grid(row=2, column=0)
bins_e = tk.Entry(settings)
bins_e.insert(0, bins)
bins_b = tk.Button(settings, text="Update", command=bins_callback)
bins_e.grid(row=2, column=1)
bins_b.grid(row=2, column=2)

# Voltage Update
voltageUpdate_label = tk.Label(settings, text="Voltage Update Time (ms)").grid(row=2, column=4)
voltageUpdate_e = tk.Entry(settings)
voltageUpdate_e.insert(0, voltageUpdate)
voltageUpdate_b = tk.Button(settings, text="Update", command=voltageUpdate_callback)
voltageUpdate_e.grid(row=2, column=5)
voltageUpdate_b.grid(row=2, column=6)

# Blower Flow Rate
blowerFlow_label = tk.Label(settings, text="Blower Flow Rate (L/min)").grid(row=3, column=3)
blowerFlow_e = tk.Entry(settings)
blowerFlow_e.insert(0, blowerFlow)
blowerFlow_b = tk.Button(settings, text="Update", command=blowerFlow_callback)
blowerFlow_e.grid(row=4, column=3)
blowerFlow_b.grid(row=4, column=4)

# File Location
data_storage_label = tk.Label(settings, text="Data Storage (File Location)").grid(row=5, column=3)
file_e = tk.Entry(settings)
file_e.insert(0, file)
file_b = tk.Button(settings, text="Update", command=file_callback)
file_e.grid(row=6, column=3)
file_b.grid(row=6, column=4)

# Voltage Cycle Button
voltageCycle_label = tk.Label(settings, text="Voltage Cycle").grid(row=1, column=3)
voltageCycle_b = tk.Button(settings, text="On", command=voltageCycle_callback)
voltageCycle_b.grid(row=2, column=3)

# Current Set Voltage
voltageSetPoint_label = tk.Label(settings, text="Set Voltage").grid(row=3, column=5)
voltageSetPoint_e = tk.Entry(settings)
voltageSetPoint_e.insert(0, labjackVoltage * voltageFactor)
voltageSetPoint_e.grid(row=4, column=5)

# Current Monitor Voltage
supplyVoltage_label = tk.Label(settings, text="Supply Voltage").grid(row=5, column=5)
supplyVoltage_e = tk.Entry(settings)
supplyVoltage_e.insert(0, voltageMonitor)
supplyVoltage_e.grid(row=6, column=5)

# Start Button
start_b = tk.Button(settings, text="Run", command=onStart)
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
