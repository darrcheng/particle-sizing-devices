import sys
import tkinter as tk

from smpscontrol import SMPS


# Allow config file to be passed from .bat file or directly from code
if len(sys.argv) > 1:
    config_file = sys.argv[1]
else:
    config_file = "..\\sample_config.yml"

root = tk.Tk()
app = SMPS(root, config_file)
root.mainloop()
