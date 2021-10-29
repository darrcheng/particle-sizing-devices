import tkinter as tk
import csv
import time
from tkinter.constants import FALSE
import u3
import LabJackPython
from simple_pid import PID
import threading
d = u3.U3()

###########################################
#test parameters
#Blower Scale =
#dac0_val = d.voltageToDACBits(0.5)
#d.getFeedback(u3.DAC0_8(dac0_val))

#HV scale = 2000:1

# Initalize Labjack U3
d.getCalibrationData()
dac0_val = d.voltageToDACBits(2.2, dacNumber=0, is16Bits= False)
d.getFeedback(u3.DAC0_8(dac0_val))

dac1_val = d.voltageToDACBits(0)
d.getFeedback(u3.DAC1_8(dac1_val))

# Returns flow rate corrected by temperature and pressure  
#def flowUpdate():
#    slpm = (d.getAIN(3))/0.2
#    tFactor = (tempUpdate()+273.15)/273.15
#    pFactor = 100/pUpdate()
#    return (slpm*tFactor*pFactor)
    
# Returns Temperature Probe input
# Temperature Probe in FIO0, correction factor: temp x 100
def tempUpdate():
    return ((d.getAIN(0))/0.01)

# Returns RH Probe input
# RH probe in FIO1, correction factor: (RH-0.958)/0.0307
def rhUpdate():
    return (((d.getAIN(1))-0.958)/0.0307)

# Returns Pressure Probe (PSense) input
# Psense in FIO2, correction factor (P-0.2)/0.045
def pUpdate():
    return ((d.getAIN(2)-0.2)/0.045)


############################################

# Default Settings
voltageCycle = True
trialCount = 0
lvl = 10   # Lower Voltage Limit #V will be 100
uvl = 200  # Upper Voltage Limit #V will be 8000' 
bins = 10
pidp = 0.2*(7)        #PID Proportional Gain
pidi = 0.4*(7)/(1.2)      #PID Integral Gain
pidd = 0.066*(7)*(1.2)     #PID Derivative Gain
file = 'c:\\Users\\user\\Documents\\trialrun.csv'
voltageUpdate = 100 #ms
blowerFlow = 5 # Set Blower Flow Rate in [LPM]
timer = 0
control = 0
labjackVoltage = 0

# Initalizing threads for running blower and voltage setting codes

b = None
v = None
#monitoring


#Set Flow as AIN3
def flowUpdate():
    slpm = (d.getAIN(3)-.85)/0.2
    tFactor = (tempUpdate()+273.15)/273.15
    pFactor = 100/(100+pUpdate())
#    return (slpm*tFactor*pFactor)
    return (slpm)
    #return d.getAIN(3)
"""
#Set Temperature Probe to AIN0
def tempUpdate():
    return ((d.getAIN(0))/0.01)

#Set RH Probe to AIN1
def rhUpdate():
    return (((d.getAIN(1))-0.958)/0.0307)

#Set PSense Probe to AIN1
def pUpdate():
    return ((d.getAIN(2)-.2)/0.045) """

#######################################################

# Creates the base canvas for TKinter
runtime = tk.Tk()
settings = tk.Frame(runtime)
settings.pack()

#######################################################
# Define callback function for update button in Tkinter GUI
def voltageCycle_callback(): #Not sure what this one does
    global voltageCycle
    voltageCycle = not voltageCycle
    print (voltageCycle)

def lvl_callback():
    global lvl
    lvl = lvl_e.get()

def uvl_callback():
    global uvl
    uvl = uvl_e.get()

def voltageUpdate_callback():
    global voltageUpdate
    voltageUpdate = voltageUpdate_e.get()

def bins_callback():
    global bins
    bins = bins_e.get()

def blowerFlow_callback():
    global blowerFlow
    blowerFlow = blowerFlow_e.get()
    pid.setpoint = blowerFlow

def file_callback():
    global file
    file = file_e.get()

###############################################################################

def onStart():

    #Reconfigure Start Button to Stop Button
    start_b.configure(text='Stop', command=onClose)

    #Configure PID Controller
    pid = PID(int(pidp), int(pidi), int(pidd), setpoint=int(blowerFlow))


    #Reveal the Monitoring controls
    global trialCount
    trialCount +=1
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
        global trialCount
        with open(file, mode='w',newline='') as data_file:
            data_writer = csv.writer(data_file, delimiter=',')
            data_writer.writerow(['Trial Count','Timer','Temperature','Measured'])
            while True:

                # Pause for 0.5 seconds then update timer
                # (Fix: Pull Date Time instead of arbritary time)
                time.sleep (0.2)
                timer += 0.2

                # Read temperature and update GUI
                tempRead = tempUpdate()
                temp_e.delete(0, 'end')
                temp_e.insert(0, tempRead)

                # Read RH and update GUI
                rhRead = rhUpdate()
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

                # PID Function (Fix this)
                measured = flowUpdate()
                control = pid(measured)
                
                # Write Data to CSV file
                data_writer.writerow([trialCount, timer, tempRead, measured])
                
                #Not Sure
                dac0_val = d.voltageToDACBits(1)
                d.getFeedback(u3.DAC0_8(dac0_val))
                print(d.getAIN(3))


    #By defining a foreground function, the background process can continuously run and update its input values
    def hv():
            #scan through the voltage difference, stopping at as many bins as given, for as long as given
        global lvl
        global uvl
        global bins
        global labjackVoltage

        # If voltageCycle is selected
        if voltageCycle == True:
            voltage = int(lvl)
            increment = ((int(uvl)-int(lvl))/int(bins))
            labjackVoltage = voltage/2000
            labjackIncrement = increment/2000

            for i in range(int(bins)):
                dac1_val = d.voltageToDACBits(labjackVoltage)
                d.getFeedback(u3.DAC1_8(dac1_val))
                time.sleep(voltageUpdate/1000)
                labjackVoltage += labjackIncrement
                time.sleep(voltageUpdate/1000)

            for i in range(int(bins)):
                dac1_val = d.voltageToDACBits(labjackVoltage)
                d.getFeedback(u3.DAC1_8(dac1_val))
                time.sleep(voltageUpdate/1000)
                labjackVoltage +- labjackIncrement
                time.sleep(voltageUpdate/1000)

        if voltageCycle == False:
            dac0_val = d.voltageToDACBits(labjackVoltage)
            d.getFeedback(u3.DAC0_8(dac0_val))

    #These lines actually seperate the processes to run on different threads of the processor, so they occur simultaneously
    global b
    global v
    b = threading.Thread(name = 'Blower Monitoring', target=blower)
    v = threading.Thread(name= 'High Voltage', target=hv)

    b.start()
    v.start()

def onClose():
    #Reconfigure Stop Button to Start Button
    start_b.configure(text='Run', command=onStart)

    global d
    d.close()
    runtime.destroy()

#################################################################
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

def changeText(bool):
    v = tk.BooleanVar(root)
    v.assertEqual(bool, v.get())
    return v
test = str(voltageCycle)

voltageCycle_b = tk.Button(settings, textvariable = test , command=voltageCycle_callback)
voltageCycle_b.grid(row=4,column=5)

voltageMonitor_label = tk.Label(settings, text = 'Current Voltage').grid(row=5,column=5)
voltageMonitor_e = tk.Entry(settings)
voltageMonitor_e.insert(0, labjackVoltage*2000)

# Start Button
start_b = tk.Button(settings, text="Run", command=onStart)
start_b.grid(row=9,column=3)

###############################################################################
# Tkinter for displaying values of Temperature, RH and P during run 

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
