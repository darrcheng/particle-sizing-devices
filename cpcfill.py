from labjack import ljm
import time
import sys
import traceback
from datetime import datetime

import sensors
import shared_var


def cpc_fill(handle, labjack_io, stop_threads, close_barrier):
    """Opens fill valve for 0.25 s when CPC reads NOTFULL"""

    # Close valve
    ljm.eWriteName(handle, labjack_io["fill_valve"], 0)

    # Constants for flow intervals
    curr_time = time.monotonic()
    fill_update_time = 1  # seconds
    previous_cpc_serial = []
    serial_good = True

    # Infinite Loop
    while not stop_threads.is_set():
        # Check if CPC serial is running properly
        if shared_var.cpc_serial_read == previous_cpc_serial:
            serial_good = False
        else:
            previous_cpc_serial = shared_var.cpc_serial_read
            serial_good = True

        try:
            # Check if CPC butanol reservior is not full
            if shared_var.fill_status == "NOTFULL" and serial_good == True:
                # Open valve
                ljm.eWriteName(handle, labjack_io["fill_valve"], 1)
                print("Filling")
                # Pause
                time.sleep(0.25)

                # Close valve
                ljm.eWriteName(handle, labjack_io["fill_valve"], 0)

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
    close_barrier.wait()
