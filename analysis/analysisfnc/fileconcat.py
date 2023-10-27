import os
import pandas as pd
import numpy as np
import glob
from datetime import timedelta


def import_csv_to_dataframe(file_list):
    # Create an empty DataFrame
    df = pd.DataFrame()

    # Iterate through the list of CSV files
    for file in file_list:
        # Read each CSV file into a temporary DataFrame
        temp_df = pd.read_csv(file, header=None)

        # Append the temporary DataFrame to the main DataFrame
        df = pd.concat([df, temp_df], ignore_index=True)

    # Convert the first column to datetime format
    df.iloc[:, 0] = pd.to_datetime(df.iloc[:, 0])

    return df


def add_blank_lines(df, max_gap_minutes):
    # Sort the DataFrame by the Timestamp column
    # df = df.sort_values(by='Timestamp')

    # Calculate the time difference between consecutive rows
    time_diff = df.iloc[:, 0].diff()

    # Find the indices where the time difference is greater than the specified maximum gap
    indices = df.index[time_diff > pd.Timedelta(minutes=max_gap_minutes)]

    while indices.shape > (0, 0):
        # Insert blank rows at the identified indices
        offset_index = 0
        for index in indices:
            temp_df = pd.DataFrame(
                np.nan, index=range(1), columns=range(df.shape[1])
            )
            temp_df.iloc[0, 0] = df.iloc[
                index - 1 + offset_index, 0
            ] + pd.Timedelta(minutes=max_gap_minutes)
            df = pd.concat(
                [
                    df.iloc[: index + offset_index, :],
                    temp_df,
                    df.iloc[index + offset_index :, :],
                ],
                ignore_index=True,
            )
            offset_index = offset_index + 1

        # Calculate the time difference between consecutive rows
        time_diff = df.iloc[:, 0].diff()

        # Find the indices where the time difference is greater than the specified maximum gap
        indices = df.index[time_diff > pd.Timedelta(minutes=max_gap_minutes)]

    return df
