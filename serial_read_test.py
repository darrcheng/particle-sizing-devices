import serial
import csv
import time

# Set up the serial port
ser = serial.Serial("COM1", 9600)  # Replace 'COM1' with the name of your serial port
ser.flushInput()

# Set up the CSV file
filename = "data.csv"
header = ["time", "rall", "RSF", "RIF"]  # Customize the header as needed
with open(filename, mode="w", newline="") as csv_file:
    writer = csv.writer(csv_file)
    writer.writerow(header)

# Send commands and record responses
commands = ["rall", "RSF", "RIF"]  # Add more commands as needed
while True:
    try:
        # Store responses in a list
        responses = []

        for command in commands:
            # Send command to serial port
            ser.write((command + "\n").encode())

            # Read response from serial port
            response = ser.readline().decode().rstrip()

            # Append response to the list
            responses.append(response)

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
