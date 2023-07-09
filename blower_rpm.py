# import u3

# # Open the LabJack U3
# d = u3.U3()

# # Enable the timers and counters, set FI0 for 4 analog ins = 1111 , none for EIO
# d.configIO(
#     NumberOfTimersEnabled=1, EnableCounter1=1, TimerCounterPinOffset=4, FIOAnalog=15, EIOAnalog=0
# )
# # Set the configuration for the first timer:
# t0Config = u3.TimerConfig(0, TimerMode=10, Value=0)

# d.getFeedback(
#     t0Config,
# )
# d.configTimerClock(TimerClockBase=None, TimerClockDivisor=None)
# counter = u3.Counter(1)
# timer = u3.Timer(0)
# startMeasures = d.getFeedback(timer, counter)
# startTime = startMeasures[0]
# print(startMeasures)

# import time

# time.sleep(1)

# startMeasures = d.getFeedback(timer, counter)
# time_diff = (startMeasures[0] - startTime) / 4000000
# print(startMeasures)
# print(time_diff)

# d.close()


import u3
import time
import tkinter as tk

# Open the LabJack U3
d = u3.U3()

# Enable the timers and counters, set FI0 for 4 analog ins = 1111, none for EIO
d.configIO(
    NumberOfTimersEnabled=1, EnableCounter1=1, TimerCounterPinOffset=4, FIOAnalog=15, EIOAnalog=0
)
# Set the configuration for the first timer:
t0Config = u3.TimerConfig(0, TimerMode=10, Value=0)

d.getFeedback(t0Config)
d.configTimerClock(TimerClockBase=None, TimerClockDivisor=None)
counter = u3.Counter(1)
timer = u3.Timer(0)

# Create a Tkinter window
window = tk.Tk()
window.title("Time Difference")
window.geometry("200x100")

# Create a label to display the time difference
time_label = tk.Label(window, text="Time difference: ")
time_label.pack()

previous_measurement = None
previous_count = None


def update_time_difference():
    global previous_measurement  # Declare previous_measurement as global
    global previous_count

    startMeasures = d.getFeedback(timer, counter)
    current_measurement = startMeasures[0]
    current_count = startMeasures[1]

    if previous_measurement is not None:
        time_diff = (current_measurement - previous_measurement) / 4000000
        count_diff = current_count - previous_count
        current_rpm = (count_diff / 6) / (time_diff / 60)
        time_label.config(text="Blower RPM: {:.2f}".format(current_rpm))
        
    previous_count = current_count
    previous_measurement = current_measurement
    window.after(1000, update_time_difference)


# Start updating the time difference
update_time_difference()

window.mainloop()

# Close the LabJack U3
d.close()
