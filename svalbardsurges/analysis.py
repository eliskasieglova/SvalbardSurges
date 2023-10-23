import xarray as xr
from pathlib import Path
import numpy as np
import warnings
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

def create_bins(data_path):

    # open data
    data = xr.open_dataset(data_path)

    bins = np.nanpercentile(data["dem_elevation"], np.linspace(0, 100, 6))

    return bins

def hypso_is2(input_path, bins):
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
    hypso_bins = {}

    # count bins
    #bins = np.nanpercentile(data["dem_elevation"], np.linspace(0, 100, 6))
    #bins = np.array([0, 250, 500, 750, 900])

    for year, data_subset in data.groupby(data["date"].dt.year):
        # create hypsometric bins
        hypso_subset = xdem.volume.hypsometric_binning(
            ddem=data_subset['dh'],
            ref_dem=data_subset['dem_elevation'],
            kind="custom",
            bins=bins,
            aggregation_function=np.nanmean
        )

        # append data to dictionary
        hypso_bins[year] = hypso_subset

    return hypso_bins

def hypso_dem(dems, bins, ref_dem):
    """
    Hypsometric binning of glacier elevation changes from ArcticDEM data. Function used for
    validation.

    Parameters
    ----------
    - dems
        dictionary containing paths leading to yearly DEMs
    - ref_dem
        reference DEM from 2010

    Results
    -------
    Dictionary of binned data.
    """

    # load reference DEM
    ref_dem = xdem.DEM(ref_dem)

    # create bins
    #bins = np.nanpercentile(ref_dem.data.filled(np.nan), np.linspace(0, 100, 6))
    #bins[-1] *= 1.1

    #bins = np.array([0, 250, 500, 750, 900])

    # initialize empty dictionary for storing binned data
    hypso = {}

    for year in dems:
        # create difference DEM (current year compared to 2010)
        d_dem = xdem.DEM(dems[year]) - ref_dem

        # no empty values
        if np.count_nonzero(np.isfinite(d_dem.data.filled(np.nan))) == 0:
            continue

        # hypsometric binning
        hypso[year] = xdem.volume.hypsometric_binning(ddem=d_dem.data, ref_dem=ref_dem.data, kind='custom', bins=bins)

    return hypso