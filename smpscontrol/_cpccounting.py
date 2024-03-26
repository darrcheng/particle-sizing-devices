from datetime import datetime
import sys
import threading
import time
import traceback

import labjack.ljm as ljm

# import shared_var


class CPCCount:
    def __init__(
        self, handle, config, stop_threads, close_barrier, count_queue
    ):
        self.handle = handle
        self.config = config
        self.stop_threads = stop_threads
        self.close_barrier = close_barrier
        self.count_queue = count_queue

        self.thread = threading.Thread(target=self.cpc_conc)

    def start(self):
        self.thread.start()

    def cpc_conc(self):
        labjack_io = self.config["labjack_io"]
        cpc_config = self.config["cpc_config"]
        # Start counting
        prev_time, prev_count = initalize_labjack_counting(
            self.handle, labjack_io
        )
        # prev_time = time.monotonic()
        # prev_count = 0
        count_error = False

        # Constants for update intervals
        curr_time = time.monotonic()
        update_time = 1  # seconds
        while not self.stop_threads.is_set():
            try:
                if count_error:
                    try:
                        prev_time, prev_count = initalize_labjack_counting(
                            self.handle, labjack_io
                        )
                        print("Connected to LabJack device!")
                        count_error = False
                    except ljm.LJMError:
                        print("Failed to connect to LabJack device.")

                # Clear variables used measuring pulse width
                pulse_width_list = []
                pulses = 0
                pulse_error = 0
                pulse_counter = time.monotonic()
                pulse_width_error = 0
                pulse_width = 0

                # # If counts are too high, don't pulse count
                # if shared_var.curr_count < 1e6:
                #     # Repeatedly measure the pulse width and keep an error counter
                #     while (time.monotonic() - pulse_counter) < (
                #         update_time * 0.8
                #     ) and not stop_threads.is_set():
                #         pulse_width_single = ljm.eReadName(
                #             handle, labjack_io["width"] + "_EF_READ_A_F_AND_RESET"
                #         )
                #         if pulse_width_single < 1:
                #             pulse_width_list.append(pulse_width_single)
                #         else:
                #             pulse_error = pulse_error + 1
                #         pulses = pulses + 1
                #     if pulse_width_list:
                #         raw_pulse_width = sum(pulse_width_list)
                #     else:
                #         raw_pulse_width = 0
                # else:
                #     shared_var.concentration = -9999
                #     shared_var.pulse_width = -9999
                raw_pulse_width = 0

                # Read the current count from the high-speed counter
                count = ljm.eReadName(
                    self.handle, labjack_io["counter"] + "_EF_READ_A"
                )
                curr_count = count - prev_count

                # Calculate the elapsed time since the last count
                count_time = time.monotonic()
                elapsed_time = count_time - prev_time

                # Calculate the true pulse width from counts and measured pulse width
                if (pulses - pulse_error) > 0:
                    pulse_width = raw_pulse_width * (
                        (count - prev_count) / (pulses - pulse_error)
                    )
                    # Calculate error assuming pulse errors are due to short pulses
                    if pulse_width > 0:
                        pulse_width_error = (
                            pulse_error * 50e-9 / pulse_width * 100
                        )
                else:
                    pulse_width = 0

                # Calculate the concentration
                if elapsed_time - pulse_width > 0:
                    concentration = (count - prev_count) / (
                        (elapsed_time - pulse_width)
                        * cpc_config["cpc_flowrate"]
                    )
                else:
                    concentration = -9999

                # Calculate the no deadtime concentration
                if elapsed_time > 0:
                    concentration_nodead = (count - prev_count) / (
                        (elapsed_time) * cpc_config["cpc_flowrate"]
                    )
                else:
                    concentration_nodead = -9999

                # Set the previous count and time for the next iteration
                prev_time = count_time
                prev_count = count

                # Calculate runtime
                cpc_counting_runtime = (
                    time.monotonic() - curr_time - update_time
                )

                count_data = {
                    "cpc count thread time": datetime.now(),
                    "concentration": concentration,
                    "count": curr_count,
                    "pulse width": pulse_width,
                    "pulse width error": pulse_width_error,
                    "concentration no-deadtime": concentration_nodead,
                    "cpc count runtime": cpc_counting_runtime,
                }
                self.count_queue.put(count_data)

                # Schedule the next update
                curr_time = curr_time + update_time
                next_time = curr_time + update_time - time.monotonic()
                if next_time < 0:
                    if abs(next_time) / update_time > 1:
                        curr_time = curr_time + update_time * int(
                            abs(next_time) / update_time
                        )
                    next_time = 0
                    print("Slow: CPC Pulse Counting" + str(datetime.now()))
                time.sleep(next_time)

            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print("CPC Counting: " + str(ljme) + str(datetime.now()))
                count_error = True
                time.sleep(1)

            except Exception as e:
                print("CPC Pulse Counting Error")
                print(traceback.format_exc())
                raise

        print("Shutdown: CPC Pulse Counting")
        self.close_barrier.wait()


def initalize_labjack_counting(handle, labjack_io):
    # Enable clock
    ljm.eWriteName(handle, "DIO_EF_CLOCK1_ENABLE", 0)  # Disable clock 1
    ljm.eWriteName(handle, "DIO_EF_CLOCK2_ENABLE", 0)  # Disable clock 2
    ljm.eWriteName(handle, "DIO_EF_CLOCK0_ENABLE", 0)  # Disable clock 0
    ljm.eWriteName(
        handle, "DIO_EF_CLOCK0_DIVISOR", 0
    )  # Set divisor to 1, T7 = 80 MHz
    ljm.eWriteName(
        handle, "DIO_EF_CLOCK0_ROLL_VALUE", 0
    )  # Set roll to 4294967295
    ljm.eWriteName(handle, "DIO_EF_CLOCK0_ENABLE", 1)  # Enable clock

    # Configure the specified high-speed counter to read pulses
    ljm.eWriteName(
        handle, labjack_io["counter"] + "_EF_ENABLE", 0
    )  # Disable high-speed counter
    ljm.eWriteName(
        handle, labjack_io["counter"] + "_EF_INDEX", 7
    )  # Set input as counter
    ljm.eWriteName(
        handle, labjack_io["counter"] + "_EF_ENABLE", 1
    )  # Enable high-speed counter

    # # Configure pulse width in
    # ljm.eWriteName(handle, labjack_io["width"] + "_EF_ENABLE", 0)  # Disable pulse width
    # ljm.eWriteName(handle, labjack_io["width"] + "_EF_CONFIG_A", 0)  # Set to one shot
    # ljm.eWriteName(handle, labjack_io["width"] + "_EF_INDEX", 5)  # Set input as pulse width
    # ljm.eWriteName(handle, labjack_io["width"] + "_EF_OPTIONS", 0)  # Set to clock 0
    # ljm.eWriteName(handle, labjack_io["width"] + "_EF_ENABLE", 1)  # Enable pulse width

    # Initialize time variables and previous count
    prev_time = time.monotonic()
    prev_count = ljm.eReadName(
        handle, labjack_io["counter"] + "_EF_READ_A_AND_RESET"
    )
    return prev_time, prev_count
