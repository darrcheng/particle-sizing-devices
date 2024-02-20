####################Default Variable Settings####################
# General Settings
stopThreads = False  # Bool to help close program

# Flow Settings
pidp = 0.2  # PID Proportional Gain
pidi = 0  # PID Integral Gain
pidd = 0  # PID Derivative Gain
control = 0  # PID Output
blower_flow_set = 0  # Set Blower Flow Rate in [LPM]

# Flow Measurement Variables
flow_read = 0  # Measured flow rate
rh_read = 0  # Measured relative humidity
temp_read = 0  # Measured temperature
press_read = 0  # Measured pressure

# Voltage Cycle Settings
voltageCycle = True  # Turn voltage cycling on and off
low_dia_lim = 1  # Lower Voltage Limit #V will be 100
high_dia_lim = 2  # Upper Voltage Limit #V will be 8000'
size_bins = 0  # Number of steps in voltage cycle
dlnDp = 0  # natural log of difference between steps
voltage_update_time = 0  # Time between each voltage step
ljvoltage_set_out = 0  # Labjack output to control HV supply
voltage_monitor = 1  # Current voltage read from HV supply monitor
set_diameter = 0
dia_list = []
diameter_mode = ""
scan_polarity = ""

# CPC Variables
curr_count = 0
concentration = 0
concentration_nodead = 0
pulse_width = 0
pulse_width_error = 0
fill_status = ""

# Runtime
blower_runtime = 0
voltage_runtime = 0
voltage_monitor_runtime = 0
data_logging_runtime = 0
cpc_counting_runtime = 0
serial_runtime = 0

# GUI
graph_line = []

# CPC Serial
cpc_serial_read = []
