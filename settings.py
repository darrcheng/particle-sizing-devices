####################Default Variable Settings####################
# General Settings
file = "C:\\Users\\d95st\\Blower_Box\\trialrun.csv"  # File Name
stopThreads = False  # Bool to help close program
timer = 0
dma = "nanodma"

# Flow Settings
pidp = 0.2  # PID Proportional Gain
pidi = 0  # PID Integral Gain
pidd = 0  # PID Derivative Gain
control = 0  # PID Output
blower_flow_set = 15  # Set Blower Flow Rate in [LPM]

# Flow Measurement Variables
flow_read = 0  # Measured flow rate
rh_read = 0  # Measured relative humidity
temp_read = 0  # Measured temperature
press_read = 0  # Measured pressure

# Voltage Cycle Settings
voltageCycle = True  # Turn voltage cycling on and off
low_voltage_lim = 10  # Lower Voltage Limit #V will be 100
high_voltage_lim = 200  # Upper Voltage Limit #V will be 8000'
bins = 10  # Number of steps in voltage cycle
voltage_update_time = 5000  # Time between each voltage step
ljvoltage_set_out = 0  # Labjack output to control HV supply
voltage_monitor = 0  # Current voltage read from HV supply monitor
voltage_set_scaling = 10000 / 5  # Scaling for HV Supply

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
