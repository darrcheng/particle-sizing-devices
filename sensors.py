from labjack import ljm
import time

# Returns Temperature Probe input
def temp_update(handle, temp_input):
    """Returns temperature from sensor input
    Correction factor: temperature = voltage * 100"""
    return ljm.eReadName(handle, temp_input) / 0.01


# Returns RH Probe input
def rh_update(handle, rh_input):
    """Returns RH from sensor input (not temperatur adjusted)
    Correction factor:"""
    return (ljm.eReadName(handle, rh_input) / 5 - 0.16) / 0.0062


# Returns Pressure Probe (PSense) input
def press_update(handle, press_input):
    """Returns pressure from sensor input
    Correction factor: pressure = (voltage-0.278)/0.045"""
    return (ljm.eReadName(handle, press_input) - 0.278) / 0.045


# Returns Flow Reading (Averaged over 5 readings, 1ms apart)
def flow_update(handle, flow_read_input):
    """Returns flow reading in SLPM, 5 averaged readings 1 ms apart"""
    slpm = []
    flow_measure_repeat = 0
    while flow_measure_repeat < 5:
        slpm.append((ljm.eReadName(handle, flow_read_input) - 0.9947) / 0.1714)
        # tFactor = (temp_update(handle, temp_input) + 273.15) / 273.15
        # pFactor = 100 / (100 + press_update(handle, press_input))
        time.sleep(0.001)
        flow_measure_repeat += 1
    avg_slpm = sum(slpm) / len(slpm)
    return avg_slpm


# Returns HV Supply Voltage
def hv_update(handle, voltage_monitor_input):
    """Returns HV montior reading, 5 averaged readings 1 ms apart"""
    voltage = []
    voltage_measure_repeat = 0
    while voltage_measure_repeat < 5:
        voltage.append(ljm.eReadName(handle, voltage_monitor_input) * 1000)
        time.sleep(0.001)
        voltage_measure_repeat += 1
    avg_voltage = sum(voltage) / len(voltage)
    return avg_voltage
