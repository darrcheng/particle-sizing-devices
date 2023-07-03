import glob
import os
import matplotlib.pyplot as plt
import traceback

import fileconcat
import psdgraph

file_date = "2023-06-26"
dma_list = ["longdma", "nanodma"]
for dma in dma_list:
    try:
        # dma = "longdma"
        folder_path = "C:\\Users\\d95st\\Box Sync\\Jen Lab Data Archive\\SMPS\\"  # Replace with the actual folder path

        # List of CSV files to import
        file_list = glob.glob(
            folder_path + file_date + "\\" + dma + "_invert*.csv"
        )  # Replace with the pattern matching your CSV files

        # Import CSV files into a DataFrame
        dataframe = fileconcat.import_csv_to_dataframe(file_list)

        # Add blank lines where the gap in timestamps is more than 11 minutes
        dataframe = fileconcat.add_blank_lines(dataframe, 15)

        # Save the resulting DataFrame
        subfolder_path = os.path.join(os.getcwd(), "data")
        os.makedirs(subfolder_path, exist_ok=True)
        dataframe.to_csv("data\\" + dma + "_" + file_date + ".csv", index=False, header=False)

        # Convert dataframe to numpy array
        time_data = dataframe.iloc[:, 0].to_numpy(dtype="M")
        data = dataframe.iloc[:, 1:].to_numpy()

        # Graph particle size distribution
        plot = psdgraph.graph_psd(file_date, dma, time_data, data)

        # Save Graph
        plt.savefig("data\\" + dma + "_" + file_date + ".png", dpi=300)

        # Show graph
        plt.show()

    except IndexError:
        print("No " + dma + " data")
    except Exception as e:
        print(e)
        print(traceback.format_exc())
