import time

from labjack import ljm

# Labjack IO
blower_io = "TDAC2"
flowmeter_io = "AIN0"

# Load Labjack
handle = ljm.openS("T7", "ANY", "ANY")
info = ljm.getHandleInfo(handle)
print(info)

# Prompt use to enter blower voltage
blower_voltage = float(input("Enter the blower voltage: "))
ljm.eWriteName(handle, blower_io, blower_voltage)

# Let blower come to speed
print("Blower is coming to speed...")
time.sleep(10)

# Read flowmeter voltage once a second for a minute
flowmeter_voltages = []
for i in range(60):
    print(f"Reading flowmeter voltage... ({i + 1}/60)")
    flowmeter_voltages.append(ljm.eReadName(handle, flowmeter_io))
    time.sleep(1)

# Average the flowmeter voltages
flowmeter_voltage_avg = sum(flowmeter_voltages) / len(flowmeter_voltages)
print("Flowmeter voltage: " + str(flowmeter_voltages))
print("Average flowmeter voltage: " + str(flowmeter_voltage_avg))

# Check if user is done measuring flow
done = "n"  # Default to "n"
while done == "n":
    done = input("Are you done measuring flow? (y/n): ")
    if done.lower() == "n":
        print("Please run the script again.")
    else:
        # Turn off blower
        ljm.eWriteName(handle, blower_io, 0)
        ljm.close(handle)
