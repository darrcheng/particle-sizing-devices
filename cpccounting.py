import labjack.ljm as ljm
import time
import shared_var


def cpc_conc(handle, labjack_io, stop_threads, cpc_config, count_e):
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
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_CONFIG_A", 1)  # Set to one shot
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_INDEX", 5)  # Set input as pulse width
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_OPTIONS", 0)  # Set to clock 0
    ljm.eWriteName(handle, labjack_io["width"] + "_EF_ENABLE", 1)  # Enable pulse width

    ljm.writeLibraryConfigS("LJM_STREAM_RECEIVE_TIMEOUT_MS", 0)

    # Initialize time variables and previous count
    prev_time = time.monotonic()
    prev_count = ljm.eReadName(handle, labjack_io["counter"] + "_EF_READ_A")

    # # Initalize streaming for pulse width
    # aScanListNames = ["DIO0_EF_READ_A"]  # Scan list names to stream
    # numAddresses = len(aScanListNames)
    # aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
    # ljm.eStreamStart(handle, 1000, numAddresses, aScanList, 2000)

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
            shared_var.curr_count = count - prev_count
            # settings.pulse_width = ljm.eReadName(handle, labjack_io["width"] + "_EF_READ_A_F")
            # settings.pulse_width = 0
            # data = ljm.eStreamRead(handle)

            pulse_width_list = []
            pulses = 0
            pulse_error = 0
            pulse_counter = time.monotonic()
            while time.monotonic() - pulse_counter < 0.8:
                pulse_width_single = ljm.eReadName(handle, labjack_io["width"] + "_EF_READ_A_F")
                if pulse_width_single < 1:
                    pulse_width_list.append(pulse_width_single)
                else:
                    pulse_error = pulse_error + 1
                pulses = pulses + 1
            raw_pulse_width = sum(pulse_width_list)

            # Extract the pulse width from the stream data
            if raw_pulse_width > 0:
                shared_var.pulse_width = (
                    raw_pulse_width  * ((count - prev_count) / (pulses - pulse_error))
                )
                if shared_var.pulse_width > 0:
                # print("Max Error: ", pulse_error * 50e-9 / shared_var.pulse_width * 100, " %")
                    shared_var.pulse_width_error = pulse_error * 50e-9 / shared_var.pulse_width * 100
            else:
                shared_var.pulse_width = 0

            # Calculate the elapsed time since the last count
            count_time = time.monotonic()
            elapsed_time = count_time - prev_time

            # Calculate the count rate in pulses per second
            shared_var.concentration = (count - prev_count) / (
                (elapsed_time - shared_var.pulse_width) * cpc_config["cpc_flowrate"]
            )
            dead_time = shared_var.pulse_width

            # Display the count rate in the label widget
            count_e.delete(0, "end")
            count_e.insert(0, shared_var.concentration)

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
    # ljm.eStreamStop(handle)
