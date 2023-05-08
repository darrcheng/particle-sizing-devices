import labjack.ljm as ljm
import time
import shared_var
import sys


def cpc_conc(handle, labjack_io, stop_threads, close_barrier, cpc_config, count_e):
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

    # # Initalize streaming for pulse width
    # ljm.writeLibraryConfigS("LJM_STREAM_RECEIVE_TIMEOUT_MS", 0)
    # aScanListNames = ["DIO0_EF_READ_A"]  # Scan list names to stream
    # numAddresses = len(aScanListNames)
    # aScanList = ljm.namesToAddresses(numAddresses, aScanListNames)[0]
    # ljm.eStreamStart(handle, 1000, numAddresses, aScanList, 2000)

    # Constants for update intervals
    curr_time = time.monotonic()
    update_time = 1  # seconds
    while not stop_threads.is_set():
        try:
            # Read the current count from the high-speed counter
            # print("right after try")
            count = ljm.eReadName(handle, labjack_io["counter"] + "_EF_READ_A")
            shared_var.curr_count = count - prev_count

            # Calculate the elapsed time since the last count
            count_time = time.monotonic()
            elapsed_time = count_time - prev_time

            # # Read in stream pulse width data
            # data = ljm.eStreamRead(handle)

            # Clear variables used measuring pulse width
            pulse_width_list = []
            pulses = 0
            pulse_error = 0
            pulse_counter = time.monotonic()
            shared_var.pulse_width_error = 0
            shared_var.pulse_width = 0

            # If counts are too high, don't pulse count
            if shared_var.curr_count < 1e6:
                # Repeatedly measure the pulse width and keep an error counter
                # print("before while loop")
                while (time.monotonic() - pulse_counter) < (
                    update_time * 0.8
                ) and not stop_threads.is_set():
                    # print("yes")
                    # print(time.monotonic() - pulse_counter)
                    pulse_width_single = ljm.eReadName(
                        handle, labjack_io["width"] + "_EF_READ_A_F_AND_RESET"
                    )
                    # pulse_width_single = ljm.eReadAddresses(handle, 1, [3600], [3])[0]
                    if pulse_width_single < 1:
                        pulse_width_list.append(pulse_width_single)
                    else:
                        pulse_error = pulse_error + 1
                    pulses = pulses + 1
                    # time.sleep(0.001)
                    # print(pulse_width_single)
                if pulse_width_list:
                    raw_pulse_width = sum(pulse_width_list)
                else:
                    raw_pulse_width = 0

                # raw_pulse_width = 0.5
                # print("while loop breaks")

                # Calculate the true pulse width from counts and measured pulse width
                # print(pulses-pulse_error)
                if raw_pulse_width > 0 and (pulses - pulse_error) > 0:
                    shared_var.pulse_width = raw_pulse_width * (
                        (count - prev_count) / (pulses - pulse_error)
                    )
                    # Calculate error assuming pulse errors are due to short pulses
                    if shared_var.pulse_width > 0:
                        shared_var.pulse_width_error = (
                            pulse_error * 50e-9 / shared_var.pulse_width * 100
                        )
                else:
                    shared_var.pulse_width = 0

                # Calculate the count rate in pulses per second
                if elapsed_time - shared_var.pulse_width > 0:
                    shared_var.concentration = (count - prev_count) / (
                        (elapsed_time - shared_var.pulse_width) * cpc_config["cpc_flowrate"]
                    )
                else:
                    shared_var.concentration = -9999
            else:
                shared_var.concentration = -9999
                shared_var.pulse_width = -9999

            # print("do I get here?")

            # Display the count rate in the label widget
            # count_e.delete(0, "end")
            # print("here?")
            # count_e.insert(0, shared_var.concentration)
            # print("i guess not here")
            # Set the previous count and time for the next iteration
            prev_time = count_time
            prev_count = count

            shared_var.cpc_counting_runtime = time.monotonic() - curr_time - update_time

            # Schedule the next update
            curr_time = curr_time + update_time
            next_time = curr_time + update_time - time.monotonic()
            # print(next_time)
            if next_time < 0:
                if abs(next_time) / update_time > 1:
                    curr_time = curr_time + update_time * int(abs(next_time) / update_time)
                next_time = 0
                print("Slow: CPC Pulse Counting")
            time.sleep(next_time)
            # print("after sleep")

        except ljm.LJMError:
            ljme = sys.exc_info()[1]
            print(ljme)
            time.sleep(1)

        except Exception as e:
            print("CPC Pulse Counting Error", e)
            raise
    print("Shutdown: CPC Pulse Counting")
    close_barrier.wait()
