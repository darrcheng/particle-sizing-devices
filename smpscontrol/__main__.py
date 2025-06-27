import tkinter as tk
from . import SMPS

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Instrument GUI")

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

    app = SMPS(root, "..\\long_config.yml")
    root.mainloop()
