import xarray as xr
from pathlib import Path
import numpy as np
import warnings
from matplotlib import pyplot as plt
import rasterio as rio

# Catch a deprecation warning that arises from skgstat when importing xDEM
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem

def IS2_DEM_difference(dem_path, is2_path, glacier_outline, output_path):
    """
    Get elevation difference between ICESat-2 data and reference DEM.

    Parameters
    ----------
    - dem
        reference dem
    - is2
        ICESat-2 dataset

    Returns
    -------
    ICESat-2 dataset with the additional values of "dem_elevation" (retained values of reference DEM)
    and "dh" (difference between IS2 and reference DEM)
    """

    # if subset already exists open dataset
    if output_path.is_file():
        return output_path

    is2 = xr.open_dataset(is2_path)

    with rio.open(dem_path) as raster, warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='.*converting a masked element to nan.*')
        is2["dem_elevation"] = "index", np.fromiter(
            raster.sample(
                np.transpose([is2.easting.values, is2.northing.values]),
                masked=True
            ),
            dtype=raster.dtypes[0],
            count=is2.easting.shape[0]
        )

    # subtract IS2 elevation from DEM elevation (with elevation correction)
    is2["dh"] = is2["h_te_best_fit"] - is2["dem_elevation"] - 31.55

    # save as netcdf file
    is2.to_netcdf(output_path)

    return output_path

def hypsometric_binning(input_path):
    """
    Hypsometric binning of glacier elevation changes.

    Parameters
    ----------
    - input_path
        path to IS2 dataset containing the variables 'dh' and 'dem_elevation'

    Results
    -------
    Pandas dataframe of elevation bins, plot of hypsometric elevation change for each year in dataset.
    """

    # open data
    data = xr.open_dataset(input_path)

    # empty dictionary to append binned elevation differences by year
    hypso_bins = { }
    stddev = { }

    # count bins
    bins = np.nanpercentile(data["dem_elevation"], np.linspace(0, 100, 6))

    for year, data_subset in data.groupby(data["date"].dt.year):
        # create hypsometric bins
        hypso_subset = xdem.volume.hypsometric_binning(
            ddem=data_subset["dh"],
            ref_dem=data_subset["dem_elevation"],
            kind="custom",
            bins=bins,
            aggregation_function=np.nanmean
        )

        # append data to dictionary
        hypso_bins[year] = hypso_subset

    # convert absolute values to relative
    for year in hypso_bins:
        if year != 2022:
            hypso_bins[year]['abs'] = hypso_bins[year].value - hypso_bins[year+1].value

    return hypso_bins