import glob
import os
import matplotlib.pyplot as plt
import traceback

import fileconcat
import psdgraph
import inversioncorrect
import mergedist

# file_dates = ["2023-08-08"]
file_dates = [
    "2023-09-04",
    "2023-09-05",
    "2023-09-06",
    "2023-09-07",
    "2023-09-08",
    "2023-09-09",
]
dma_list = ["longdma", "nanodma"]


for file_date in file_dates:
    dma_times = {}
    dma_dists = {}
    print("File Date:", file_date)
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
            dataframe.to_csv(
                "data\\" + dma + "_" + file_date + ".csv",
                index=False,
                header=False,
            )

            print("Finshed: Data Concat")

            # Convert dataframe to numpy array
            time_data = dataframe.iloc[:, 0].to_numpy(dtype="M")
            data = dataframe.iloc[:, 1:].to_numpy()

            # Correct inverted data for CPC detection efficiency and sampling losses
            data, export = inversioncorrect.data_correction(
                dma, time_data, data
            )
            export.to_csv(
                "data\\" + dma + "_" + file_date + "_corrected.csv",
                index=False,
                header=False,
            )

            # Save data into dictionary
            dma_times[dma] = time_data
            dma_dists[dma] = data

            # Graph particle size distribution
            plot = psdgraph.graph_psd(file_date, dma, time_data, data)

            # Save Graph
            plt.savefig("data\\" + dma + "_" + file_date + ".png", dpi=300)

            print("Finshed: Plot Save")

            # Show graph
            # plt.show()

        except IndexError:
            print("No " + dma + " data")
        except Exception as e:
            print(e)
            print(traceback.format_exc())

    try:
        # Merge long column and nano size distributions
        export, diameters, dndlndp, time = mergedist.combine_smps(
            dma_times, dma_dists
        )

        export.to_csv(
            "data\\SMPS_" + file_date + ".csv",
            index=False,
            header=False,
        )

        psdgraph.graph_merged(file_date, time, diameters, dndlndp)
        plt.savefig("data\\SMPS_" + file_date + ".png", dpi=300)
    except Exception as e:
        print(e)
        print(traceback.format_exc())

    plt.close("all")
