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
