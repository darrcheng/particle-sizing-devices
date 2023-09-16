import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib import dates
from matplotlib.ticker import LogLocator, LogFormatter
from matplotlib import dates
import matplotlib.dates as mdates


def graph_psd(file_date, dma, time_data, data):
    # Isolate numpy arrays
    time_data = np.copy(time_data)
    data = np.copy(data)

    # Graph settings for long vs nano DMA
    if dma == "longdma":
        # num_bins = 60
        conc_cbar_min = 10
        conc_cbar_max = 1050
        dn_cbar_min = 1000
        dn_cbar_max = 100050
        y_min = 8
        y_max = 500
    elif dma == "nanodma":
        # num_bins = 30
        conc_cbar_min = 10
        conc_cbar_max = 1050
        dn_cbar_min = 1000
        dn_cbar_max = 100050
        y_min = 1
        y_max = 50

    # Split data into diameter, concentration, dndlogdp, skip first bin (reset bin)
    num_bins = int(data.shape[1] / 3)
    dp = data[:, 1:num_bins]
    conc = data[:, num_bins + 1 : 2 * num_bins]
    dndlog = data[:, 2 * num_bins + 1 : 3 * num_bins]

    # Set 0's to nan's
    conc[conc == 0] = np.nan
    dndlog[dndlog == 0] = np.nan

    # Set nan's to 0
    dp[np.isnan(dp)] = 0

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
    norm = colors.LogNorm(vmin=conc_cbar_min, vmax=conc_cbar_max)

    # Plot concentration contour
    csf = ax1.contourf(
        time,
        dp.T,
        conc.T,
        np.logspace(np.log10(conc_cbar_min), np.log10(conc_cbar_max), 200),
        cmap=cmap,
        norm=norm,
        extend="both",
    )
    ax1.set_yscale("log")
    ax1.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))
    ax1.set_title("Particle Concentration (" + dma + ": " + file_date + ")")
    ax1.set_xlabel("Time [US/Eastern]")
    ax1.set_ylabel(r"Diameter [nm]", fontsize=10)
    ax1.set_ylim(y_min, y_max)

    # Plot colorbar
    # cbar = fig.colorbar(csf, ticks=LogLocator(subs=range(10)))
    major_ticks = [10**1, 10**2, 10**3]
    cbar = format_log_colorbar(fig, csf, major_ticks)
    cbar.ax.set_ylabel("Concentration [$\mathregular{p/cm^3}$]")

    ax2 = fig.add_subplot(2, 1, 2)
    # plt.subplots_adjust(left=0.1, right=0.99, top=0.9, bottom=0.1)

    # Set dndlndp colormap
    cmap = "jet"
    norm = colors.LogNorm(vmin=dn_cbar_min, vmax=dn_cbar_max)

    # Plot dndlndp contour
    csf = ax2.contourf(
        time,
        dp.T,
        dndlog.T,
        np.logspace(np.log10(dn_cbar_min), np.log10(dn_cbar_max), 200),
        cmap=cmap,
        norm=norm,
        extend="both",
    )
    ax2.set_yscale("log")
    ax2.xaxis.set_major_formatter(dates.DateFormatter("%H:%M"))
    ax2.set_title("dNdlnDp (" + dma + ": " + file_date + ")")
    ax2.set_xlabel("Time [US/Eastern]")
    ax2.set_ylabel(r"Diameter [nm]", fontsize=10)
    ax2.set_ylim(y_min, y_max)

    # Plot colorbar
    # cbar = fig.colorbar(csf, ticks=LogLocator(subs=range(10)))
    # cbar.ax.set_ylabel("dN/dlogDp [$\mathregular{p/cm^3}$]")
    # Plot colorbar
    major_ticks = [10**3, 10**4, 10**5]

    cbar = format_log_colorbar(fig, csf, major_ticks)
    cbar.ax.set_ylabel("dN/dlogDp [$\mathregular{p/cm^3}$]")

    return fig


def graph_merged(file_date, time_data, diameters, dndlndp):
    # Isolate numpy arrays
    time_data = np.copy(time_data)
    diameters = np.copy(diameters)
    dndlndp = np.copy(dndlndp)

    # Preprocess arrays
    y = np.arange(0, diameters.shape[1])
    time, y = np.meshgrid(time_data, y)
    dndlndp[dndlndp == 0] = np.nan
    diameters[np.isnan(diameters)] = 0

    # Constants
    dn_cbar_min = 1000
    dn_cbar_max = 100050
    y_min = 1
    y_max = 500
    cmap = "jet"
    norm = colors.LogNorm(vmin=dn_cbar_min, vmax=dn_cbar_max)
    major_ticks = [10**3, 10**4, 10**5]

    # Graphing
    fig, ax = plt.subplots(figsize=(12, 5))
    plt.subplots_adjust(left=0.1, right=0.99, top=0.9, bottom=0.1, hspace=0.5)

    csf = ax.contourf(
        time,
        diameters.T,
        dndlndp.T,
        np.logspace(np.log10(dn_cbar_min), np.log10(dn_cbar_max), 200),
        cmap=cmap,
        norm=norm,
        extend="both",
    )
    ax.set_yscale("log")
    ax.set_title("Size Distribution (" + file_date + ")")
    ax.set_xlabel("Time [US/Eastern]")
    ax.set_ylabel(r"Diameter [nm]", fontsize=10)
    ax.set_ylim(y_min, y_max)

    # Plot colorbar
    cbar = format_log_colorbar(fig, csf, major_ticks)
    cbar.ax.set_ylabel("dN/dlogDp [$\mathregular{p/cm^3}$]")

    # Pulled from https://matplotlib.org/3.4.3/gallery/ticks_and_spines/date_concise_formatter.html
    locator = mdates.AutoDateLocator(minticks=3, maxticks=7)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    return fig


# Set major tick labels in the format `10^3`, `10^4`, etc.
def format_func(value, tick_number):
    return r"$10^{{{:d}}}$".format(int(np.log10(value)))


def format_log_colorbar(fig, csf, major_ticks):
    cbar = fig.colorbar(csf, ticks=major_ticks)

    cbar.ax.yaxis.set_major_formatter(plt.FuncFormatter(format_func))

    # Set minor ticks between the decades
    cbar.ax.yaxis.set_minor_locator(
        LogLocator(base=10, subs=np.arange(2, 10) * 0.1)
    )
    return cbar
