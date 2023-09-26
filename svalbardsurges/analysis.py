import xarray as xr
from pathlib import Path
import numpy as np
import warnings
from statistics import stdev
from matplotlib import pyplot as plt

# Catch a deprecation warning that arises from skgstat when importing xdem
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem

def subset_is2(is2_data, bounds, label):
    """
    Subset IS2 data using specified bounds.

    The easting and northing variables need to be loaded in memory, so this is a computationally expensive task.
    The function is cached using the label argument to speed up later calls.

    Parameters
    ----------
    - is2_data
        the ICESat-2 data to subset
    - bounds
        bounding box to use (requires the keys: "left", "right", "bottom", "top")
    - label
        a label to assign when caching the subset result

    Returns
    -------
    A subset IS2 dataset within the given bounds.
    """

    # path to cached file
    output_name = Path(f"cache/{label}-is2.nc")

    # if subset already exists open dataset
    if output_name.is_file():
        return xr.open_dataset(output_name)

    # subset data based on bounds
    subset = is2_data.where(
        (is2_data.easting > bounds["left"]) & (is2_data.easting < bounds["right"]) & (is2_data.northing > bounds["bottom"]) & (
                    is2_data.northing < bounds["top"]), drop=True)

    output_name.parent.mkdir(exist_ok = True)
    subset.to_netcdf(output_name)

    return subset

def IS2_DEM_difference(dem, is2, label):
    """
    Get elevation difference between ICESat-2 data and reference DEM.

    Parameters
    ----------
    - dem
        reference dem
    - is2
        ICESat-2 dataset
    - label
        label to be assigned to the output dataset

    Returns
    -------
    ICESat-2 dataset with the additional values of "dem_elevation" (retained values of reference DEM)
    and "dh" (difference between IS2 and reference DEM)
    """

    # path to cached file
    output_name = Path(f"cache/{label}-is2-dh.nc")

    # if subset already exists open dataset
    if output_name.is_file():
        return xr.open_dataset(output_name)

    #svalbardsurges.plotting.plot_pts(is2, 'h_te_best_fit')

    # assign DEM elevation as a variable to the IS2 data
    is2["dem_elevation"] = "index", dem.value_at_coords(is2.easting, is2.northing)

    # subtract IS2 elevation from DEM elevation
    is2["dh"] = is2["dem_elevation"] - is2["h_te_best_fit"]

    # filter out nan
    is2 = is2.where(is2.dem_elevation < 2000)
    is2 = is2.dropna(dim='index')

    # save as netcdf file
    is2.to_netcdf(output_name)

    return is2

def hypsometric_binning(data):
    """
    Hypsometric binning of glacier elevation changes.

    Parameters
    ----------
    - data
        IS2 dataset containing the variables 'dh' and 'dem_elevation'

    Results
    -------
    Pandas dataframe of elevation bins, plot of hypsometric elevation change for each year in dataset.
    """

    # empty dictionary to append binned elevation differences by year to
    hypso_bins = { }
    stddev = { }
    bins = np.nanpercentile(data["dem_elevation"], np.linspace(0, 100, 11))

    for year, data_subset in data.groupby(data["date"].dt.year):
        # correct elevation and add it to dataset todo: better conversion
        data_subset['dh_corr'] = data_subset['dh'] + 31.55
        data[year] = data_subset['dh_corr']

        # create hypsometric bins
        hypso = xdem.volume.hypsometric_binning(ddem=data_subset["dh_corr"], ref_dem=data_subset["dem_elevation"], kind="custom", bins=bins)
        hypso_bins[year] = hypso

        # compute standard deviation
        stddev[year] = np.std(data_subset['dh'])

    # scatterplot of available data points that we have
    #scatter = plt.scatter(data.easting, data.northing, c=data["date"].dt.year, cmap='hsv', s=0.5)
    #plt.title(year)
    #legend1 = plt.legend(*scatter.legend_elements(), loc="upper left", title="Classes")
    #plt.show()

    # convert cumulative values to absolute and visualize the hypsometric analysis
    for year in hypso_bins:
        if year != 2022:
            hypso_bins[year]['abs'] = hypso_bins[year].value - hypso_bins[year+1].value

    return hypso_bins, stddev
