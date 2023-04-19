import labjack.ljm as ljm
import time
import settings


def cpc_conc(handle, labjack_io, stop_threads, count_e):
    # Configure clock
    ljm.eWriteName(handle, "DIO_EF_CLOCK1_ENABLE", 0)  # Disable clock 1
    ljm.eWriteName(handle, "DIO_EF_CLOCK2_ENABLE", 0)  # Disable clock 2
    ljm.eWriteName(handle, "DIO_EF_CLOCK0_ENABLE", 0)  # Disable clock 0
    ljm.eWriteName(handle, "DIO_EF_CLOCK0_DIVISOR", 0)  # Set divisor to 1, T7 = 80 MHz
    ljm.eWriteName(handle, "DIO_EF_CLOCK0_ROLL_VALUE", 0)  # Set roll to 4294967295
    ljm.eWriteName(handle, "DIO_EF_CLOCK0_ENABLE", 1)  # Enable clock

    # Configure the specified high-speed counter to read pulses
    ljm.eWriteName(handle, labjack_io["counter"] + "_EF_ENABLE", 0)  # Disable high-speed counter
    ljm.eWriteName(handle, labjack_io["counter"] + "_EF_INDEX", 7)  # Set input as counter
    ljm.eWriteName(handle, labjack_io["counter"] + "_EF_ENABLE", 1)  # Enable high-speed counter

    # Configure pulse width in
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_ENABLE", 0)  # Disable pulse width
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_CONFIG_A", 0)  # Set to one shot
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_INDEX", 5)  # Set input as pulse width
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_OPTIONS", 0)  # Set to clock 0
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_ENABLE", 1)  # Enable pulse width

    # Initialize time variables and previous count
    prev_time = time.monotonic()
    prev_count = ljm.eReadName(handle, labjack_io["counter"] + "_EF_READ_A")

    # Initalize streaming for pulse width
    aScanListNames = ["DIO0_EF_READ_A"]  # Scan list names to stream
    numAddresses = len(aScanListNames)
    aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
    ljm.eStreamStart(handle, 2000, numAddresses, aScanList, 2000)

    # Constants for update intervals
    curr_time = time.monotonic()
    update_time = 1  # seconds
    while True:
        try:
            # Break out of loop on close
            if stop_threads.is_set() == True:
                print("Shutdown: CPC Pulse Counting")
                break

            # Get the current UTC time
            utc_time = time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())

            # Read the current count from the high-speed counter
            count = ljm.eReadName(handle, labjack_io["counter"] + "_EF_READ_A")
            settings.curr_count = count - prev_count
            # settings.pulse_width = ljm.eReadName(handle, labjack_io["width"] + "_EF_READ_A_F")
            # settings.pulse_width = 0
            data = ljm.eStreamRead(handle)
            curSkip = data.count(-9999.0)

            # Extract the pulse width from the stream data
            settings.pulse_width = sum(data[0]) / 80e6 * ((count - prev_count) / 2000)

            # Calculate the elapsed time since the last count
            count_time = time.monotonic()
            elapsed_time = count_time - prev_time

            # Calculate the count rate in pulses per second
            settings.concentration = (count - prev_count) / (
                (elapsed_time - settings.pulse_width) * settings.cpc_flowrate
            )
            dead_time = settings.pulse_width

            # Display the count rate in the label widget
            count_e.delete(0, "end")
            count_e.insert(0, settings.concentration)

            # Set the previous count and time for the next iteration
            prev_time = count_time
            prev_count = count

            # Schedule the next update
            curr_time = curr_time + update_time
            next_time = curr_time + update_time - time.monotonic()
            if next_time < 0:
                next_time = 0
            time.sleep(next_time)

        except BaseException as e:
            print("CPC Pulse Counting Error")
            print(e)
            break

    ljm.eWriteName(handle, labjack_io["width"] + "_EF_ENABLE", 0)  # Disable pulse width
    ljm.eWriteName(handle, labjack_io["counter"] + "_EF_ENABLE", 0)  # Disable high-speed counter
    ljm.eStreamStop(handle)
