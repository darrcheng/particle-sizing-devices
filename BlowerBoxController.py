import tkinter as tk
import csv
import time
from datetime import datetime #Pulls current time from system
from datetime import timedelta #Calculates difference in time
from tkinter.constants import FALSE
import u3
from LJTick import LJTickDAC
from simple_pid import PID
import threading
d = u3.U3()

####################Labjack Startup####################
# Initalize Labjack U3
d.getCalibrationData()
dac0_val = d.voltageToDACBits(2.2, dacNumber=0, is16Bits= False)
d.getFeedback(u3.DAC0_8(dac0_val))

# Define LJTick DAC as set in FIO4
tdac = LJTickDAC(d, 4)

# Set HV Supply to 0V
dac1_val = d.voltageToDACBits(0)
d.getFeedback(u3.DAC1_8(dac1_val))

####################Labjack Read Functions####################
# Returns Temperature Probe input
# Temperature Probe in FIO0, correction factor: temp x 100
def tempUpdate():
    return ((d.getAIN(7))/0.01)

# Returns RH Probe input
# RH probe in FIO1, only ouputs sensor RH, not corrected for temperature
def rhUpdate():
    #return (((d.getAIN(1))-0.958)/0.0307)
    return (d.getAIN(1)/5-0.16)/0.0062

# Returns Pressure Probe (PSense) input
# Psense in FIO2, correction factor (P-0.2)/0.045
def pUpdate():
#    return ((d.getAIN(2)-0.2)/0.045)
    return ((d.getAIN(2)-0.278)/0.045)

# Returns HV Supply Voltage
def vUpdate():
    return(d.getAIN(0)*1000)

# Returns Flow Reading (Averaged over 5 readings, 1ms apart)
def flowUpdate():
    slpm = []
    flow_measure_repeat = 0 
    while flow_measure_repeat < 5:
        slpm.append((d.getAIN(3)-0.9947)/0.1714)
        tFactor = (tempUpdate()+273.15)/273.15
        pFactor = 100/(100+pUpdate())
        time.sleep(0.001)
        flow_measure_repeat += 1
    avg_slpm = sum(slpm)/len(slpm)
    return (avg_slpm)

####################Default Variable Settings####################
# General Settings
file = 'c:\\Users\\user\\Documents\\trialrun.csv'   # File Name
timer = 0

# Flow Settings
pidp = 0.2                                      # PID Proportional Gain
pidi = 0                                  # PID Integral Gain
pidd = 0                               # PID Derivative Gain
control = 0                                         # PID Output
blowerFlow = 5                                      # Set Blower Flow Rate in [LPM]

'''# Flow Settings
pidp = 0.2*0.8                                      # PID Proportional Gain
pidi = 0.4*0.8/0.8                                  # PID Integral Gain
pidd = 0.0666*0.8*0.8                               # PID Derivative Gain
control = 0                                         # PID Output
blowerFlow = 5                                      # Set Blower Flow Rate in [LPM]
'''

# Voltage Cycle Settings
voltageCycle = True                                 # Turn voltage cycling on and off
lvl = 10                                            # Lower Voltage Limit #V will be 100
uvl = 200                                           # Upper Voltage Limit #V will be 8000' 
bins = 10                                           # Number of steps in voltage cycle
voltageUpdate = 1000                                # Time between each voltage step
labjackVoltage = 0                                  # Labjack output to control HV supply
voltageMonitor = 0                                  # Current voltage read from HV supply monitor
voltageFactor = 10000/4.64                          # Scaling for HV Supply

# Initalizing threads for running blower and voltage setting codes
b = None        # Bloewr Control
v = None        # Voltage Set
m = None        # Voltage Monitor


####################TKinter Button Functions####################
# Define callback function for update button in Tkinter GUI
# Voltage Cycle Button
# Switches between True and False and changes button text
def voltageCycle_callback(): 
    global voltageCycle
    voltageCycle = not voltageCycle
    if voltageCycle == True:
        voltageCycle_b.config(text = "On")
    if voltageCycle == False:
        voltageCycle_b.config(text = "Off")
    print (voltageCycle)

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
    start_b.configure(text='Stop', command=onClose)

    # Configure PID Controller
    pid = PID(pidp, pidi, pidd, setpoint=blowerFlow)
    pid.output_limits = (-0.25,0.25)

    # Set Variables
    global control
    global labjackVoltage
    global start_time; start_time = datetime.now()

    
    # Reveal the Monitoring controls
    temp_label.pack()
    temp_e.pack()
    rh_label.pack()
    rh_e.pack()
    p_label.pack()
    p_e.pack()
    flow_label.pack()
    flow_e.pack()

    # Controls the blower with PID code to ensure the flow rate stays at the specified flow rate
    def blower():
        global timer

        # Set flow to 0 LPM
        tdac.update(0,0)
        time.sleep(5)
        flow_time = start_time
        flow_elapsed = 0

        # Open CSV logging file
        with open(file, mode='w',newline='') as data_file:
            data_writer = csv.writer(data_file, delimiter=',')
            data_writer.writerow(['Timer','Flow Rate [LPM]','Set Voltage [V]','Actual Voltage[V]','Temperature [C]','RH[%]','Pressure[kPa]'])
            
            # Infinite Loop
            while True:
                # Pause for 0.5 seconds then update timer
                # (Fix: Pull Date Time instead of arbritary time)
                time.sleep (0.05)
                timer += 0.2
                            #Pause until next date time increment is reached
                flow_milliseconds = 0
                while flow_milliseconds < 500:
                    flow_time_new = datetime.now()
                    flow_milliseconds = int((flow_time_new - flow_time).total_seconds()*1000)
                flow_elapsed += float((flow_time_new - flow_time).total_seconds())
                flow_time = flow_time_new


                # Read temperature and update GUI
                tempRead = tempUpdate()
                temp_e.delete(0, 'end')
                temp_e.insert(0, tempRead)

                # Read RH, correct for temperature and update GUI
                rhRead = rhUpdate()/(1.0546-0.00216*tempRead)
                rh_e.delete(0, 'end')
                rh_e.insert(0, rhRead)

                # Read Pressure and update GUI
                pRead = pUpdate()
                p_e.delete(0,'end')
                p_e.insert(0, pRead)

                # Read Flow Rate and update GUI
                flowRead = flowUpdate()
                flow_e.delete(0,'end')
                flow_e.insert(0, flowRead)

                # PID Function 
                measured = flowUpdate()
                control = 0.016*blowerFlow + 1.8885 + pid(measured)
                tdac.update(control,0)
                
                # Write Data to CSV file
                data_writer.writerow([flow_time,flow_elapsed,measured,labjackVoltage*voltageFactor,voltageMonitor,tempRead,rhRead,pRead])
            

    # Controls the DMA voltage scanning
    def hv():
        global lvl
        global uvl
        global bins
        global voltageUpdate
        global labjackVoltage

        while True:

            # If voltageCycle is on, cycle through voltages
            while voltageCycle == True:
                # Set variables based on GUI inputs
                voltage = int(lvl)
                increment = ((int(uvl)-int(lvl))/int(bins))
                labjackVoltage = voltage/voltageFactor
                labjackIncrement = increment/voltageFactor

                # Loop through voltages between upper and lower limits
                for i in range(int(bins)):
                    # Stop cycle at current voltage if voltage cycle is turned off
                    if voltageCycle == False:
                            break
                    
                    #Set Voltage to Labjack and update GUI
                    dac1_val = d.voltageToDACBits(labjackVoltage)
                    d.getFeedback(u3.DAC1_8(dac1_val))
                    voltageSetPoint_e.delete(0,'end')
                    voltageSetPoint_e.insert(0, labjackVoltage*voltageFactor)
                    
                    #Pause then increment
                    time.sleep(voltageUpdate/1000)
                    labjackVoltage += labjackIncrement

            # If voltage cycle is turned off, set HV supply to paused voltage        
            while voltageCycle == False:
                dac1_val = d.voltageToDACBits(labjackVoltage)
                d.getFeedback(u3.DAC1_8(dac1_val))

    # Define Voltage Monitor
    def vIn():
        global voltageMonitor
        while True:
            # Read in HV supply voltage and update GUI
            voltageMonitor = vUpdate()
            supplyVoltage_e.delete(0,'end')
            supplyVoltage_e.insert(0,voltageMonitor)

            time.sleep(0.2)

    # Define and start threads
    global b; b = threading.Thread(name = 'Blower Monitoring', target=blower)
    global v; v = threading.Thread(name= 'High Voltage', target=hv)
    global m; m = threading.Thread(name= 'Voltage Monitor', target=vIn)
    b.start()
    v.start()
    m.start()

def onClose():
    #Reconfigure Stop Button to Start Button
    start_b.configure(text='Run', command=onStart)

    global d
    d.close()
    runtime.destroy()

####################GUI Creation####################
# Creates the base canvas for TKinter
runtime = tk.Tk()
settings = tk.Frame(runtime)
settings.pack()

####################Tkinter Widgdets####################
# Create the TKinter widgets that allow for manual DMA Blower settings

# Set Point Values Title
setpoint_title = tk.Label(settings, text = 'Set Point Values').grid(row=0, column=3)

# Lower Voltage Limit
lvl_label = tk.Label(settings, text = 'Lower Voltage Limit (V)').grid(row=1, column=0)
lvl_e = tk.Entry(settings)
lvl_e.insert(0, lvl)
lvl_b = tk.Button(settings, text="Update", command=lvl_callback)
lvl_e.grid(row=1,column=1)
lvl_b.grid(row=1,column=2)

# Upper Voltage Limit
uvl_label = tk.Label(settings, text = 'Upper Voltage Limit (V)').grid(row=1,column=4)
uvl_e = tk.Entry(settings)
uvl_e.insert(0, uvl)
uvl_b = tk.Button(settings, text="Update", command=uvl_callback)
uvl_e.grid(row=1,column=5)
uvl_b.grid(row=1,column=6)

# Bins
bins_label = tk.Label(settings, text = 'Bins').grid(row=2,column=0)
bins_e = tk.Entry(settings)
bins_e.insert(0, bins)
bins_b = tk.Button(settings, text="Update", command=bins_callback)
bins_e.grid(row=2,column=1)
bins_b.grid(row=2,column=2)

# Voltage Update
voltageUpdate_label = tk.Label(settings, text = 'Voltage Update Time (ms)').grid(row=2,column=4)
voltageUpdate_e = tk.Entry(settings)
voltageUpdate_e.insert(0, voltageUpdate)
voltageUpdate_b = tk.Button(settings, text="Update", command=voltageUpdate_callback)
voltageUpdate_e.grid(row=2,column=5)
voltageUpdate_b.grid(row=2,column=6)

# Blower Flow Rate
blowerFlow_label = tk.Label(settings, text = 'Blower Flow Rate (L/min)').grid(row=3,column=3)
blowerFlow_e = tk.Entry(settings)
blowerFlow_e.insert(0, blowerFlow)
blowerFlow_b = tk.Button(settings, text="Update", command=blowerFlow_callback)
blowerFlow_e.grid(row=4,column=3)
blowerFlow_b.grid(row=4,column=4)

# File Location 
data_storage_label = tk.Label(settings, text = 'Data Storage (File Location)').grid(row=5, column=3)
file_e = tk.Entry(settings)
file_e.insert(0, file)
file_b = tk.Button(settings, text="Update", command=file_callback)
file_e.grid(row=6,column=3)
file_b.grid(row=6,column=4)

# Voltage Cycle Button
voltageCycle_label = tk.Label(settings, text = 'Voltage Cycle').grid(row=1,column=3)
voltageCycle_b = tk.Button(settings, text = "On" , command=voltageCycle_callback)
voltageCycle_b.grid(row=2,column=3)

#Current Set Voltage
voltageSetPoint_label = tk.Label(settings, text = 'Set Voltage').grid(row=3,column=5)
voltageSetPoint_e = tk.Entry(settings)
voltageSetPoint_e.insert(0, labjackVoltage*voltageFactor)
voltageSetPoint_e.grid(row=4,column = 5)

# Current Monitor Voltage
supplyVoltage_label = tk.Label(settings, text = 'Supply Voltage').grid(row=5,column=5)
supplyVoltage_e = tk.Entry(settings)
supplyVoltage_e.insert(0, voltageMonitor)
supplyVoltage_e.grid(row=6,column=5)

# Start Button
start_b = tk.Button(settings, text="Run", command=onStart)
start_b.grid(row=9,column=3)

####################Initally Hidden Tkinter Widgets####################

# Define current temperature label
temp_label = tk.Label(runtime, text = 'Temperature (C)')
temp_e = tk.Entry(runtime)

# Define current RH label
rh_label = tk.Label(runtime, text = 'Relative Humidity')
rh_e = tk.Entry(runtime)

# Define current pressure label
p_label = tk.Label(runtime, text = 'Pressure')
p_e = tk.Entry(runtime)

#Define flow rate label
flow_label = tk.Label(runtime, text = 'Flow sLPM')
flow_e = tk.Entry(runtime)

#############################################################
#Populate the root window with navigation buttons
runtime.protocol("WM_DELETE_WINDOW", onClose)
runtime.mainloop()
''''''
