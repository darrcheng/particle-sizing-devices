from labjack import ljm
import time


# Returns Temperature Probe input
def temp_update(handle, temp_input, temp_factor):
    """Returns temperature from sensor input
    Correction factor: temperature = voltage * 100"""
    return ljm.eReadName(handle, temp_input) / temp_factor


# Returns RH Probe input
def rh_update(handle, rh_input, curr_temp):
    """Returns RH from sensor input
    Correction factor:"""
    sensor_rh = (ljm.eReadName(handle, rh_input) / 5 - 0.16) / 0.0062
    true_rh = (sensor_rh) / (1.0546 - 0.00216 * curr_temp)
    return true_rh


# Returns Pressure Probe (PSense) input
def press_update(handle, press_input):
    """Returns pressure from sensor input
    Correction factor: pressure = (voltage-0.278)/0.045"""
    return (ljm.eReadName(handle, press_input) - 0.278) / 0.045


# Returns Flow Reading (Averaged over 5 readings, 1ms apart)
def flow_update(handle, flow_read_input, flow_factor, flow_offset):
    """Returns flow reading in SLPM, 5 averaged readings 1 ms apart"""
    slpm = []
    flow_measure_repeat = 0
    while flow_measure_repeat < 5:
        flow_rate = (ljm.eReadName(handle, flow_read_input) - flow_offset) * flow_factor
        slpm.append(flow_rate)
        # tFactor = (temp_update(handle, temp_input) + 273.15) / 273.15
        # pFactor = 100 / (100 + press_update(handle, press_input))
        time.sleep(0.001)
        flow_measure_repeat += 1
    avg_slpm = sum(slpm) / len(slpm)
    return avg_slpm


# Returns HV Supply Voltage
def hv_update(handle, voltage_monitor_input, voltage_factor, voltage_offset):
    """Returns HV montior reading, 5 averaged readings 1 ms apart"""
    voltage_list = []
    voltage_measure_repeat = 0
    while voltage_measure_repeat < 5:
        voltage = (ljm.eReadName(handle, voltage_monitor_input) - voltage_offset)* voltage_factor 
        voltage_list.append(voltage)
        time.sleep(0.001)
        voltage_measure_repeat += 1
    avg_voltage = sum(voltage_list) / len(voltage_list)
    return avg_voltage
