from datetime import datetime
import sys
import threading
import time
import traceback

from labjack import ljm

# import sensors
# import shared_var


class CPCFill:
    def __init__(self, handle, config, stop_threads, close_barrier, fill_queue):
        self.handle = handle
        self.config = config
        self.stop_threads = stop_threads
        self.close_barrier = close_barrier
        self.fill_queue = fill_queue

        self.thread = threading.Thread(target=self.cpc_fill)

    def start(self):
        self.thread.start()

    def cpc_fill(self):
        """Opens fill valve for 0.25 s when CPC reads NOTFULL"""
        labjack_io = self.config["labjack_io"]

        # Close valve
        ljm.eWriteName(self.handle, labjack_io["fill_valve"], 0)

        # Constants for flow intervals
        curr_time = time.monotonic()
        fill_update_time = 1  # seconds
        previous_cpc_serial = []
        serial_good = True

        # Infinite Loop
        while not self.stop_threads.is_set():
            # # Check if CPC serial is running properly
            # if shared_var.cpc_serial_read == previous_cpc_serial:
            #     serial_good = False
            # else:
            #     previous_cpc_serial = shared_var.cpc_serial_read
            #     serial_good = True

            try:
                # Check if CPC butanol reservior is not full
                try:
                    fill_status = self.fill_queue.get_nowait()
                except:
                    fill_status = "FULL"
                if fill_status == "NOTFULL":
                    # Open valve
                    ljm.eWriteName(self.handle, labjack_io["fill_valve"], 1)
                    print(str(datetime.now()) + ": Filling")
                    # Pause
                    time.sleep(0.25)

                    # Close valve
                    ljm.eWriteName(self.handle, labjack_io["fill_valve"], 0)

                # Schedule the next update
                curr_time = curr_time + fill_update_time
                next_time = curr_time + fill_update_time - time.monotonic()
                if next_time < 0:
                    next_time = 0
                time.sleep(next_time)

            except ljm.LJMError:
                ljme = sys.exc_info()[1]
                print("CPC Fill Valve: " + str(ljme) + str(datetime.now()))
                time.sleep(1)

            except BaseException as e:
                print("CPC Fill Valve Error")
                print(traceback.format_exc())
                break
        print("Shutdown: CPC Fill Valve")
        self.close_barrier.wait()
