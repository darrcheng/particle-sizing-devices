import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib import colors
from matplotlib import dates
from matplotlib.ticker import LogLocator

from matplotlib import dates
import matplotlib.dates as mdates


def interleaf_arrays(a, b):
    # Determine array size
    a_row, a_col = a.shape
    b_row, b_col = b.shape

    # Create new array
    data = np.zeros([a_row, a_col + b_col])
    data[:, ::2] = a
    data[:, 1::2] = b

    return data


def interpolate_size_dist(nano_avg_dia, nano_avg_dndlndp):
    # Interpolate nano bins
    nano_interp_dia = np.zeros(
        [nano_avg_dia.shape[0], nano_avg_dia.shape[1] - 1]
    )
    for i in range(nano_interp_dia.shape[1]):
        lo_dia = np.log(nano_avg_dia[:, i])
        hi_dia = np.log(nano_avg_dia[:, i + 1])
        nano_interp_dia[:, i] = np.exp((lo_dia + hi_dia) / 2)

    # Interpolate nano dndlndlp
    nano_interp_dndlndp = np.zeros(nano_interp_dia.shape)
    for i in range(nano_avg_dia.shape[0]):
        nano_interp_dndlndp[i] = np.interp(
            np.log(nano_interp_dia[i]),
            np.log(nano_avg_dia[i]),
            nano_avg_dndlndp[i],
        )

    # Interleaf interpolated bins
    nano_avg_dia = interleaf_arrays(nano_avg_dia, nano_interp_dia)
    nano_avg_dndlndp = interleaf_arrays(nano_avg_dndlndp, nano_interp_dndlndp)
    return nano_avg_dia, nano_avg_dndlndp


def overlap_averaging(nano_avg_dndlndp, long_avg_dndlndp, overlap_dia):
    # Calculate ln(dp_low/dp_high)
    avg_divis = np.log(overlap_dia[:, 0] / overlap_dia[:, -1])

    # Calculate nano factor
    nano_fact = np.log(overlap_dia / overlap_dia[:, -1][:, None])
    nano_fact[nano_fact > 0] = 0

    # Calculate long factor
    long_fact = np.log(overlap_dia[:, 0][:, None] / overlap_dia)
    long_fact[long_fact > 0] = 0

    # Average bins
    overlap_dndlndp = (
        nano_fact * nano_avg_dndlndp + long_fact * long_avg_dndlndp
    ) / avg_divis[:, None]

    # Check for Nan's
    overlap_dndlndp[np.isnan(long_avg_dndlndp)] = nano_avg_dndlndp[
        np.isnan(long_avg_dndlndp)
    ]
    overlap_dndlndp[np.isnan(nano_avg_dndlndp)] = long_avg_dndlndp[
        np.isnan(nano_avg_dndlndp)
    ]

    return overlap_dndlndp


def merge_smps(long_data, nano_data):
    # Constants for bin numbers going from bins 25 nm to 42 nm
    nano_lo = 26
    nano_hi = 30
    long_lo = 18
    long_hi = 26

    # Pull out diameters and dndlndp
    nano_tot_cols = nano_data.shape[1]
    nano_bins = int(nano_tot_cols / 3)
    nano_diameters = nano_data[:, 0:nano_bins]
    nano_dndlndp = nano_data[:, 2 * nano_bins : 3 * nano_bins]

    long_tot_cols = long_data.shape[1]
    long_bins = int(long_tot_cols / 3)
    long_diameters = long_data[:, 0:long_bins]
    long_dndlndp = long_data[:, 2 * long_bins : 3 * long_bins]

    # Pull out overlap region
    nano_avg_dia = nano_diameters[:, nano_lo - 1 : nano_hi]
    nano_avg_dndlndp = nano_dndlndp[:, nano_lo - 1 : nano_hi]
    long_avg_dia = long_diameters[:, long_lo - 1 : long_hi]
    long_avg_dndlndp = long_dndlndp[:, long_lo - 1 : long_hi]

    # Interpolate nanoSMPS size distribution
    nano_avg_dia, nano_avg_dndlndp = interpolate_size_dist(
        nano_avg_dia, nano_avg_dndlndp
    )

    # Use nanoSMPS as diameter bins unless there's no data except nan's
    overlap_dia = nano_avg_dia
    overlap_dia[np.isnan(nano_avg_dia)] = long_avg_dia[np.isnan(nano_avg_dia)]

    # Interpolate long column to match nano
    for i in range(overlap_dia.shape[0]):
        long_avg_dndlndp[i] = np.interp(
            np.log(overlap_dia[i]), np.log(long_avg_dia[i]), long_avg_dndlndp[i]
        )

    # Combine the overlap region
    overlap_dndlndp = overlap_averaging(
        nano_avg_dndlndp, long_avg_dndlndp, overlap_dia
    )

    # Concat higher and lower bins
    lo_dia = nano_diameters[:, : nano_lo - 1]
    lo_dndlndp = nano_dndlndp[:, : nano_lo - 1]
    hi_dia = long_diameters[:, long_hi:]
    hi_dndlndp = long_dndlndp[:, long_hi:]

    diameters = np.column_stack([lo_dia, overlap_dia, hi_dia])
    dndlndp = np.column_stack([lo_dndlndp, overlap_dndlndp, hi_dndlndp])

    return diameters, dndlndp


def ten_min_round(tm):
    # Convert numpy to datetime
    # tm = long_start.tolist()

    # Round to closest 10 minute mark
    tm += timedelta(minutes=5)
    tm -= timedelta(
        minutes=tm.minute % 10, seconds=tm.second, microseconds=tm.microsecond
    )
    return tm


def find_time_diff(dma_times, start_end):
    if start_end == "start":
        long_start = dma_times["longdma"][0].tolist()
        long_start = ten_min_round(long_start)

        nano_start = dma_times["nanodma"][0].tolist()
        nano_start = ten_min_round(nano_start)

        if nano_start == long_start:
            ref_time = None
            add_time = None
        elif nano_start < long_start:
            ref_time = nano_start
            add_time = "longdma"
        elif nano_start > long_start:
            ref_time = long_start
            add_time = "nanodma"

    elif start_end == "end":
        long_end = dma_times["longdma"][-1].tolist()
        long_end = ten_min_round(long_end)

        nano_end = dma_times["nanodma"][-1].tolist()
        nano_end = ten_min_round(nano_end)

        if nano_end == long_end:
            ref_time = None
            add_time = None
        elif nano_end > long_end:
            ref_time = nano_end
            add_time = "longdma"
        elif nano_end < long_end:
            ref_time = long_end
            add_time = "nanodma"

    return ref_time, add_time


def add_timestamps(dma_times, ref_time, add_time, start_end):
    added_lines = 0

    if start_end == "start":
        long_start = dma_times[add_time][0].astype(datetime)

        while ref_time < long_start:
            # Convert the first timestamp to a Python datetime object
            first_timestamp = dma_times[add_time][0].astype(datetime)

            # Calculate 10 minutes before the first timestamp
            new_timestamp = first_timestamp - timedelta(minutes=10)

            # Convert the new timestamp back to numpy datetime64 format
            new_timestamp_np = np.datetime64(new_timestamp)

            # Append the new timestamp to the start of the array
            dma_times[add_time] = np.insert(
                dma_times[add_time], 0, new_timestamp_np
            )

            # Round to closest 10 minute mark
            long_start = ten_min_round(new_timestamp)

            added_lines += 1

    if start_end == "end":
        long_end = dma_times[add_time][-1].astype(datetime)
        while long_end < ref_time:
            # Convert the last timestamp to a Python datetime object
            last_timestamp = dma_times[add_time][-1].astype(datetime)

            # Calculate 10 minutes after the last timestamp
            new_timestamp = last_timestamp + timedelta(minutes=10)

            # Convert the new timestamp back to numpy datetime64 format
            new_timestamp_np = np.datetime64(new_timestamp)

            # Append the new timestamp to the start of the array
            dma_times[add_time] = np.append(
                dma_times[add_time], new_timestamp_np
            )

            # Round to closest 10 minute mark
            long_end = ten_min_round(new_timestamp)

    return dma_times, added_lines


def add_blank_datalines(dma_times, dma_dists, add_time, added_lines):
    # Add blank lines to data array
    data = np.empty(
        [dma_times[add_time].shape[0], dma_dists[add_time].shape[1]]
    )
    data[:] = np.nan
    data[added_lines : dma_dists[add_time].shape[0] + added_lines] = dma_dists[
        add_time
    ]
    dma_dists[add_time] = data

    return dma_dists


def align_smps_dist(dma_times, dma_dists):
    # Find earlier time and difference in time
    earlier_time, add_time = find_time_diff(dma_times, "start")

    # If one SMPS has time stamps before the other, add lines so they match
    if earlier_time:
        dma_times, added_lines = add_timestamps(
            dma_times, earlier_time, add_time, "start"
        )
        dma_dists = add_blank_datalines(
            dma_times, dma_dists, add_time, added_lines
        )
        # Find later time and difference in times
    later_time, add_time = find_time_diff(dma_times, "end")

    # If one SMPS has time stamps after the other, add lines so they match
    if later_time:
        dma_times, added_lines = add_timestamps(
            dma_times, later_time, add_time, "end"
        )
        dma_dists = add_blank_datalines(
            dma_times, dma_dists, add_time, added_lines
        )
    return dma_times, dma_dists


def combine_smps(dma_times, dma_dists):
    if len(dma_times) == 2:
        # Align nano and long column distributions
        dma_times, dma_dists = align_smps_dist(dma_times, dma_dists)

        # Merge SMPS Distributions
        diameters, dndlndp = merge_smps(
            dma_dists["longdma"], dma_dists["nanodma"]
        )
        time = dma_times["nanodma"]
    elif "nanodma" in dma_times.keys():
        diameters = dma_dists["nanodma"][:, 0:30]
        dndlndp = dma_dists["nanodma"][:, 60:90]
        time = dma_times["nanodma"]
    else:
        diameters = dma_dists["longdma"][:, 0:60]
        dndlndp = dma_dists["longdma"][:, 120:180]
        time = dma_times["longdma"]

    data = np.concatenate((diameters, dndlndp), axis=1)
    time_export = pd.DataFrame(time)
    data_export = pd.DataFrame(data)
    export = pd.concat([time_export, data_export], axis=1)
    return export, diameters, dndlndp, time
