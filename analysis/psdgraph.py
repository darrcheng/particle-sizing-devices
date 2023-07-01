import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib import dates
from matplotlib.ticker import LogLocator


def graph_psd(file_date, dma, time_data, data):
    # Graph settings for long vs nano DMA
    if dma == "longdma":
        x = 60
        cbar_min = 10
        cbar_max = 1050
        y_min = 1
        y_max = 500
    elif dma == "nanodma":
        x = 30
        cbar_min = 0.001
        cbar_max = 2
        y_min = 1
        y_max = 50

    # Split data into diameter, concentration, dndlogdp
    dp = data[:, 1:x]
    conc = data[:, x + 1 : 2 * x]
    dndlog = data[:, 2 * x + 1 : 3 * x]

    # Set 0's to nan's
    conc[conc == 0] = "nan"
    dndlog[dndlog == 0] = "nan"

    # Create meshgrid for time
    y = np.arange(0, dp.shape[1])
    time, y = np.meshgrid(time_data, y)
    dndlog[dndlog == 0] = -999

    # Create plot frame
    fig = plt.figure(figsize=(12, 5))
    ax1 = fig.add_subplot(2, 1, 1)
    plt.subplots_adjust(left=0.1, right=0.99, top=0.9, bottom=0.1, hspace=0.5)

    # Set concentration colormap
    cmap = "jet"
    norm = colors.LogNorm(vmin=cbar_min, vmax=cbar_max)

    # Plot concentration contour
    csf = ax1.contourf(
        time, dp.T, conc.T, np.arange(cbar_min, cbar_max), cmap=cmap, norm=norm, extend="both"
    )
    ax1.set_yscale("log")
    ax1.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))
    ax1.set_title("Particle Concentration (" + dma + ": " + file_date + ")")
    ax1.set_xlabel("Time [US/Eastern]")
    ax1.set_ylabel(r"Diameter [nm]", fontsize=10)
    ax1.set_ylim(y_min, y_max)

    # Plot colorbar
    cbar = fig.colorbar(csf, ticks=LogLocator(subs=range(10)))
    cbar.ax.set_ylabel("Concentration [$\mathregular{p/cm^3}$]")

    ax2 = fig.add_subplot(2, 1, 2)
    # plt.subplots_adjust(left=0.1, right=0.99, top=0.9, bottom=0.1)

    # Set concentration colormap
    cmap = "jet"
    norm = colors.LogNorm(vmin=cbar_min, vmax=cbar_max)

    # Plot concentration contour
    csf = ax2.contourf(
        time, dp.T, dndlog.T, np.arange(cbar_min, cbar_max), cmap=cmap, norm=norm, extend="both"
    )
    ax2.set_yscale("log")
    ax2.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))
    ax2.set_title("dNdlogDp (" + dma + ": " + file_date + ")")
    ax2.set_xlabel("Time [US/Eastern]")
    ax2.set_ylabel(r"Diameter [nm]", fontsize=10)
    ax2.set_ylim(y_min, y_max)

    # Plot colorbar
    cbar = fig.colorbar(csf, ticks=LogLocator(subs=range(10)))
    cbar.ax.set_ylabel("dN/dlogDp [$\mathregular{p/cm^3}$]")

    return fig
