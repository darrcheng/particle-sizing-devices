import sys
import tkinter as tk

from smpscontrol import SMPS


# Allow config file to be passed from .bat file or directly from code
if len(sys.argv) > 1:
    config_file = sys.argv[1]
else:
    config_file = "..\\sample_config.yml"

root = tk.Tk()

# Disable Alt key menu activation to prevent GUI freezing on Windows
root.option_add("*tearOff", False)  # Disable tear-off menus
root.attributes("-toolwindow", 0)  # Ensure it's not a tool window


# Bind Alt key to do nothing (prevents menu activation)
def disable_alt(event):
    return "break"


root.bind("<Alt_L>", disable_alt)
root.bind("<Alt_R>", disable_alt)
root.bind("<KeyPress-Alt_L>", disable_alt)
root.bind("<KeyPress-Alt_R>", disable_alt)

app = SMPS(root, config_file)
root.mainloop()
