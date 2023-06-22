import serial
import csv
import time

# Set up the serial port
# ser = serial.Serial("COM5", baudrate = 115200,timeout = 0.05)  # Replace 'COM1' with the name of your serial port
ser = serial.Serial("COM6",9600,7,"E")
ser.flushInput()

# Set up the CSV file
filename = "data.csv"
#3772
# header = ["time", "concentration","instrument errors","saturator temp","condensor temp","optics temp", "cabinet temp","ambient pressure","orifice pressure","nozzle pressure","laser current","liquid level","aersol flow", "inlet flow","serial number"]  # Customize the header as needed
#3025
header = ['time','concentration','condensor temp','saturator temp','optics temp','flow','ready environment','reference detector voltage','detector voltage','pump control value','1 second counts','liquid level']
with open(filename, mode="w", newline="") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(header)

# Send commands and record responses
# commands = ["RALL", "RSF", "RIF","RSN","RCOUNT1","RCOUNT2"]  # Add more commands as needed
commands = ['RD','R1','R2','R3','R4','R5','R6','R7','RE','RB','R0']
while True:
    try:
        # Store responses in a list
        responses = []

        for command in commands:
            # Send command to serial port
            # print(1)
            ser.write((command + "\r").encode())
            # cmd = "rall\r"
            # ser.write(cmd.encode())
            # print(2)
            # print(ser.readline())
            # Read response from serial port
            response = ser.readline().decode().rstrip()
            response = response.split(",")
            # print(3)
            # Append response to the list
            responses.extend(response)

        print(responses)

        # Write responses to CSV file
        with open(filename, mode="a", newline="") as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow([time.time()] + responses)

        # Wait one second before sending the commands again
        time.sleep(1)
    except KeyboardInterrupt:
        break

# Close the serial port
ser.close()
