import tkinter as tk
from . import SMPS

if __name__ == "__main__":
    root = tk.Tk()
    root.title("Instrument GUI")
    app = SMPS(root, "..\\long_config.yml")
    root.mainloop()
