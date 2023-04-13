from labjack import ljm
import time
from datetime import datetime  # Pulls current time from system
import settings as settings


# Controls the DMA voltage scanning
def hv(handle, labjack_io, stopThreads, voltageCycle, voltageSetPoint_e):
    # global lvl  # lower voltage limit
    # global uvl  # upper voltage limit
    # global bins
    # global voltageUpdate
    # global labjackVoltage

    # Set variables based on GUI inputs
    voltage = int(settings.lvl)
    increment = (int(settings.uvl) - int(settings.lvl)) / int(settings.bins)
    print(increment)
    labjackVoltage = voltage / settings.voltageFactor
    labjackIncrement = increment / settings.voltageFactor

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
                for i in range(int(settings.bins)):
                    # Break out of loop on close
                    if stopThreads == True:
                        print(4)
                        break

                    # Stop cycle at current voltage if voltage cycle is turned off
                    if voltageCycle == False:
                        break

                    # Set Voltage to Labjack and update GUI
                    ljm.eWriteName(handle, labjack_io["voltage_set_ouput"], labjackVoltage)
                    print(labjackVoltage)
                    voltageSetPoint_e.delete(0, "end")
                    voltageSetPoint_e.insert(0, labjackVoltage * settings.voltageFactor)

                    # Pause for time specified in GUI
                    voltage_milliseconds = 0
                    while voltage_milliseconds < settings.voltageUpdate:
                        voltage_time_new = datetime.now()
                        voltage_milliseconds = (
                            int((voltage_time_new - voltage_time).total_seconds() * 1000)
                            - voltage_count * settings.voltageUpdate
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
                ljm.eWriteName(handle, labjack_io["voltage_set_ouput"], labjackVoltage)

        except BaseException:
            print(9)
            break
