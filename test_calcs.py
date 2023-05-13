from datalogging import *
import scipy.optimize

# print(calc_charged_frac(-1, 10))

# d_p = 1

# print(calc_slip_correction(d_p))

# print(calc_diffusion_coeff(d_p))

# print(calc_deposition_param(d_p, 1.58, 1500))

# deposition_param = calc_deposition_param(d_p, 1.58, 1500)

# print(calc_dma_penetration(d_p, 1.58, 1500))

# print(calc_mobility_from_voltage(1.98e4, 10000, 10000, 44.348, 1.92, 0.94))

# print(calc_voltage_from_mobility(2.16e-5, 10000, 10000, 44.348, 1.92, 0.94))

# print(calc_mobility_from_dia(1))

# # sol = scipy.optimize.broyden1(calc_mobility_from_dia, 1)
# # print(sol)

# # import math
# # from scipy.optimize import root_scalar, fsolve

# # mean_free_path = 65.1
# # slip_correction = calc_slip_correction(d_p)


# # def f(d_nm):
# #     return (
# #         slip_correction
# #         - 1
# #         - 2 * mean_free_path / d_nm * (1.257 + 0.4 * math.exp((-1.1 * d_nm) / (2 * mean_free_path)))
# #     )


# # time_start = time.monotonic_ns()
# # sol = root_scalar(f, bracket=[0.01, 100.0], method="brentq")
# # d_nm = sol.root
# # print(time.monotonic_ns() - time_start)
# # print(f"The particle diameter is {d_nm:.4f} nm.")

# # time_start = time.monotonic_ns()
# # sol = fsolve(f, 1)
# # print(sol)
# # print(time.monotonic_ns() - time_start)


# # print(calc_dia_from_mobility(2))

# # print(calc_dia_from_voltage(19568.0868174999, 10000, 10000, 44.348, 1.92659, 0.94266))

# # print(calc_mobility_from_voltage(19813.55434, 10000, 10000, 44.348, 1.92659, 0.94266))


# # print(calc_dia_from_mobility(0.0000215783251655567))
# mean_free_path = 65.1
# diameters = np.array([shared_var.low_dia_lim, shared_var.high_dia_lim])

# calc_mobility_from_dia(diameters)

# calc_slip_correction(diameters)


# slip_correction = 1 + 2 * mean_free_path / diameters * (
#     1.257 + 0.4 * np.exp((-1.1 * diameters) / (2 * mean_free_path))
# )

# slip_correction = 1 + 2 * mean_free_path / d_nm * (
#         1.257 + 0.4 * np.exp((-1.1 * d_nm) / (2 * mean_free_path))
#     )

# invert_data(12, 1, 13, -1, 1500, 15000)

# import sys


# def log_exception(type, value, traceback):
#     with open("error_log.txt", "w") as f:
#         # Get global variables and write to file
#         f.write("Global Variables:\n")
#         for name, val in globals().items():
#             f.write(f"{name} = {val}\n")

#         # Get local variables and write to file
#         f.write("\nLocal Variables:\n")
#         for name, val in locals().items():
#             f.write(f"{name} = {val}\n")

#         # Write the error message and traceback to file
#         f.write(f"\nError Type: {type}\n")
#         f.write(f"Error Message: {value}\n\n")
#         f.write("Traceback (most recent call last):\n")
#         traceback.print_tb(tb, file=f)


# # Set the excepthook to our logging function
# sys.excepthook = log_exception

# # Example code with an intentional error
# x = 5
# y = "hello"
# z = x + y  # this will cause a TypeError

# import threading
# import time
# import tkinter as tk
# from tkinter import ttk
# import tkinter
# import matplotlib.pyplot as plt
# import csv
# import pandas as pd
# import numpy
# from datetime import datetime
# import numpy as np
# from datetime import datetime
# import matplotlib.pyplot as plt
# from matplotlib import colors
# from matplotlib import dates
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

# # Implement the default Matplotlib key bindings.
# from matplotlib.backend_bases import key_press_handler
# from matplotlib.figure import Figure


# def read_csv_and_plot():
#     # Read CSV data
#     data = np.genfromtxt(
#         "longdma_invert_20230505_192423.csv", delimiter=",", skip_header=0, encoding="utf-8"
#     )
#     time_data = np.genfromtxt(
#         "longdma_invert_20230505_192423.csv",
#         dtype="M",
#         delimiter=",",
#         usecols=0,
#         skip_header=0,
#         encoding="utf-8",
#     )
#     dp = data[:, 1:61]
#     dndlog = data[:, 61:]

#     y = np.arange(0, 60)
#     time1, y = np.meshgrid(time_data, y)
#     vm = 10
#     VM = 300
#     cmap = "jet"
#     norm = colors.LogNorm(vmin=vm, vmax=VM)

#     # Create Matplotlib plot
#     fig, ax = plt.subplots()
#     csf = ax.contourf(time1, dp.T, dndlog.T, np.arange(vm, VM), cmap=cmap, norm=norm, extend="both")

#     # Add Matplotlib plot to Tkinter GUI
#     canvas = FigureCanvasTkAgg(fig, master=root1)  # A tk.DrawingArea.
#     canvas.draw()
#     canvas.get_tk_widget().pack(side=tkinter.TOP, fill=tkinter.BOTH, expand=1)


# # Create Tkinter GUI
# root1 = tk.Tk()
# root1.title("CSV Data Plot")

# root1.after(1000, read_csv_and_plot)

# # Start Tkinter event loop
# root1.mainloop()


# import tkinter as tk
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# import matplotlib.pyplot as plt
# import numpy as np

# # Create a Tkinter window
# root = tk.Tk()

# # Define a function to create the contourf plot
# def create_contourf():
#     # Generate some random data
#     x = np.linspace(0, 10, 100)
#     y = np.linspace(0, 5, 50)
#     X, Y = np.meshgrid(x, y)
#     Z = np.sin(X) + np.cos(Y)

#     # Create the plot and set its title and labels
#     fig = plt.figure(figsize=(6, 4), dpi=100)
#     ax = fig.add_subplot()
#     ax.set_title('Contourf Plot')
#     ax.set_xlabel('X Axis')
#     ax.set_ylabel('Y Axis')

#     # Plot the data as a contourf plot
#     cf = ax.contourf(X, Y, Z, levels=20)

#     # Create a Matplotlib canvas in the Tkinter window
#     canvas = FigureCanvasTkAgg(fig, master=root)
#     canvas.draw()
#     canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

# # Create a button that generates the contourf plot when clicked
# button = tk.Button(root, text='Create Contourf Plot', command=create_contourf)
# button.pack(side=tk.TOP)

# # Start the Tkinter main loop
# root.mainloop()


# import tkinter as tk
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
# import numpy as np


# import tkinter as tk
# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# # Create a Tkinter window
# root = tk.Tk()

# # Create a matplotlib figure and axis
# fig, ax = plt.subplots()

# # Create a Tkinter canvas for the figure
# canvas = FigureCanvasTkAgg(fig, master=root)
# canvas.get_tk_widget().pack()

# # Create initial data for the contour plot
# x = np.linspace(-5, 5, 101)
# y = np.linspace(-5, 5, 101)
# X, Y = np.meshgrid(x, y)
# Z = np.sin(np.sqrt(X**2 + Y**2))

# # Create the contour plot
# contour_plot = ax.contourf(X, Y, Z)


# # Define a function to update the contour plot with new data
# def update_contour():
#     # Generate new data
#     Z = np.random.rand(101, 101)
#     # Update the contour plot with the new data
#     contour_plot.set_array(Z.ravel())
#     # Redraw the figure
#     print("yes")
#     fig.canvas.draw()
#     root.after(1000, update_contour)


# # Schedule the contour plot to be updated every 10 seconds
# root.after(1000, update_contour)

# # Start the Tkinter event loop
# tk.mainloop()


# import tkinter as tk
# import numpy as np
# import matplotlib.pyplot as plt
# from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

# # Create a tkinter window
# root = tk.Tk()
# root.title("Contourf Plot")

# # Create a figure and axis for the contourf plot
# fig, ax = plt.subplots()
# canvas = FigureCanvasTkAgg(fig, master=root)
# canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)


# # Create a function to update the contourf plot
# def update_contourf():
#     # Generate new random data for the contourf plot
#     x = np.linspace(-3, 3, 100)
#     y = np.linspace(-3, 3, 100)
#     X, Y = np.meshgrid(x, y)
#     Z = np.sin(np.sqrt(X**2 + Y**2)) * np.random.rand(100, 100)

#     # Clear the axis and plot the new data
#     ax.clear()
#     ax.contourf(X, Y, Z, cmap="coolwarm")
#     ax.set_title("Contourf Plot")

#     # Redraw the canvas
#     canvas.draw()

#     # Schedule the function to be called again after 10 seconds
#     root.after(10000, update_contourf)


# # Call the update_contourf function to start the updating process
# update_contourf()

# # Run the tkinter main loop
# root.mainloop()


print(
    calc_dia_from_voltage(
        32.641533,
        9.773716661 * 1000,
        9.773716661 * 1000,
        44,
        1.92659,
        0.94266,
        12.972,
    )
)

print(calc_charged_frac(-1, 1.00001))
