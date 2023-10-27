import glob
import os
import matplotlib.pyplot as plt
import traceback

from analysisfnc import *

# Set analysis dates
dates = list(daterange.daterange("2023-10-14", "2023-10-14"))

dma_list = ["longdma", "nanodma"]

######## Scan Settings ##########
# scan_time = 10
# # Bins of overlap region, first column is 1 (Start - 09/11/23)
# overlap_bins = {
#     "nano_lo": 26,
#     "nano_hi": 30,
#     "long_lo": 18,
#     "long_hi": 26,
# }
# Bins of overlap region, first column is 1 (09/11/23 - Present)
scan_time = 5
overlap_bins = {
    "nano_lo": 27,
    "nano_hi": 30,
    "long_lo": 7,
    "long_hi": 10,
}

for date in dates:
    dma_times = {}
    dma_dists = {}
    print("File Date:", date)
    for dma in dma_list:
        try:
            # dma = "longdma"
            folder_path = f"C:\\Users\\d95st\\Box Sync\\Jen Lab Data Archive\\SMPS\\{date}"

            # List of CSV files to import
            file_list = glob.glob(folder_path + "\\" + dma + "_invert*.csv")

            # Import CSV files into a DataFrame
            dataframe = fileconcat.import_csv_to_dataframe(file_list)

            # Add blank lines where the gap in timestamps is more than 150% scan time
            dataframe = fileconcat.add_blank_lines(dataframe, scan_time * 1.5)

            # Save daily marged dataframe
            subfolder_path = os.path.join(os.getcwd(), "data")
            os.makedirs(subfolder_path, exist_ok=True)
            dataframe.to_csv(
                "psd_data\\" + dma + "_" + date + ".csv",
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
                "psd_data\\" + dma + "_" + date + "_corrected.csv",
                index=False,
                header=False,
            )

            # Save data into dictionary
            dma_times[dma] = time_data
            dma_dists[dma] = data

            # Graph particle size distribution
            plot = psdgraph.graph_psd(date, dma, time_data, data)

            # Save Graph
            plt.savefig("psd_data\\" + dma + "_" + date + ".png", dpi=300)

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
            dma_times, dma_dists, overlap_bins
        )
        # Save merged PSD size distribution
        export.to_csv(
            "psd_data\\SMPS_" + date + ".csv",
            index=False,
            header=False,
        )
        # Contour graph of size distribution
        psdgraph.graph_merged(date, time, diameters, dndlndp)
        plt.savefig("psd_data\\SMPS_" + date + ".png", dpi=300)
    except Exception as e:
        print(e)
        print(traceback.format_exc())

    plt.close("all")
