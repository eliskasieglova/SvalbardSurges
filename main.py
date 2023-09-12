import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import socket
import os
import warnings

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

import xarray as xr
import variete
import variete.vrt.vrt
import rasterio as rio
import geoutils as gu
import geopandas as gpd


# Catch a deprecation warning that arises from skgstat when importing xdem
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem


def main():

    # load IS2 data
    data = xr.open_dataset("nordenskiold_land-is2.nc")

    # set bounds for subsetting data
    bounds = {
        "bottom": 8617861,
        "right": 552643,
        "top": 8637186,
        "left": 540154
    }

    # subset IS2 data by bounds
    is2_subset = subset_is2(data, bounds, "scheelebreen")

    # plot the cropped IS2 data
    #plot_pts(is2_subset, "h_te_best_fit")

    # load DEM cropped to bounds
    dem_subset = load_dem(bounds, "scheelebreen")

    # load shapefile
    scheelebreen_shp = load_shp("Scheelebreen")

    # clip DEM to glacier area outlines
    masked_dem = mask_dem(dem_subset, scheelebreen_shp)

    # get elevation difference between IS2 and reference DEM
    is2_dh = IS2_DEM_difference(masked_dem, is2_subset, "scheelebreen")

    # plot elevation differences
    #is2_dh = xr.open_dataset("cache/scheelebreen-is2-dh.nc")
    #plot_pts(is2_dh, "dh")

    binned = hypsometric_binning("cache/scheelebreen-is2-dh.nc")

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
    cache_path = Path(f"cache/{label}-is2.nc")

    # if subset already exists open dataset
    if cache_path.is_file():
        return xr.open_dataset(cache_path)

    # subset data based on bounds
    subset = is2_data.where(
        (is2_data.easting > bounds["left"]) & (is2_data.easting < bounds["right"]) & (is2_data.northing > bounds["bottom"]) & (
                    is2_data.northing < bounds["top"]), drop=True)

    #
    cache_path.parent.mkdir(exist_ok = True)
    subset.to_netcdf(cache_path)

    return subset

def plot_pts(data, var):
    """
    Creates a scatter plot of input data.

    Works only for IS2 data as the input into the scatter plot are according to IS2 structure
    (x=data.easting, y=data.northing.

    Parameters
    ----------
    - data
        data to plot (IS2 data)
    - var
        which variable to plot (name of variable as string)
    """

    #plt.scatter(data.easting, data.northing, c=data[var])
    #plt.gca().set_aspect('equal')
    #plt.show()

def load_shp(glacier_name):
    """
    Loads a single glacier as shapefile from the GAO dataset.

    Parameters
    ----------
    - glacier name
        name of glacier we want to load as string

    Returns
    -------
    Returns .shp of the outline of selected glacier.
    """

    # paths
    file_name = Path("GAO_SfM_1936_1938_v3.shp")
    dir_name = Path("C:/Users/eliss/SvalbardSurges/GAO")
    file_path = dir_name/file_name

    # load shapefile converted to EPSG:32633
    gao = gpd.read_file(file_path).to_crs(32633)

    # filter by glacier name
    gao_glacier = gao.query(f"NAME=='{glacier_name}'")

    # if there's more glaciers with the same name select the largest one (??)

    return gao_glacier

def load_dem(bounds, label):
    """
    Loads subset of DEM using the specified bounds.

    Working with the DEM as a vrt.

    Parameters
    ----------
    - bounds
        the bounding box to use (requires the keys "left", "right", "bottom", "top")
    - label
        a label to assign when caching the result

    Returns
    -------
    A subset of the DEM within the given bounds.
    """
    # loads DEM

    # paths
    file_name = Path("S0_DTM5_2011_25163_33.tif")
    dir_name = Path("C:/Users/eliss/SvalbardSurges/DEMs")
    file_path = dir_name/("NP_"+file_name.stem)/file_name
    vrt_warped_filepath = Path(f"cache/{file_name.stem}_{label}_warped.vrt")
    vrt_cropped_filepath = Path(f"cache/{file_name.stem}_{label}_cropped.vrt")

    # convert bounds (dict) to bounding box (list)
    bbox = rio.coords.BoundingBox(**bounds)

    # warp vrt (virtual raster), dst coord system EPSG:32633 (WGS-84)
    variete.vrt.vrt.vrt_warp(vrt_warped_filepath, file_path, dst_crs=32633)

    # crop warped vrt to bbox
    variete.vrt.vrt.build_vrt(vrt_cropped_filepath, vrt_warped_filepath, output_bounds=bbox)

    # create DEM object
    dem = xdem.DEM(vrt_cropped_filepath, load_data=False)

    # plot DEM
    #dem.show()
    #plt.show()

    return dem

def mask_dem(dem, gao):
    """
    Masks DEM data by the glacier area outlines.

    Parameters
    ----------
    -dem
        DEM we want to mask
    - gao
        glacier area outline as input for masking the DEM (as .shp)

    Returns
    -------
    Masked DEM containing values only within the glacier area outlines.
    """
    # run before sampling raster

    # rasterize the shapefile to fit the DEM
    gao_rasterized = gu.Vector(gao).create_mask(dem)
    #gao_rasterized.show(cmap="Purples")
    #plt.show()

    # extract values inside the glacier area outlines
    dem.load()
    dem.set_mask(~gao_rasterized)

    # visualization
    #dem.show(cmap="Purples")
    #plt.show()

    return dem

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
    cache_path = Path(f"cache/{label}-is2-dh.nc")

    # if subset already exists open dataset
    if cache_path.is_file():
       return xr.open_dataset(cache_path)

    # assign DEM elevation as a variable to the IS2 data
    is2["dem_elevation"] = "index", dem.value_at_coords(is2.easting, is2.northing)

    # subtract IS2 elevation from DEM elevation
    is2["dh"] = is2["dem_elevation"] - is2["h_te_best_fit"]

    # save as netcdf file
    is2.to_netcdf(cache_path)

    return is2

def hypsometric_binning(data_path):
    """
    Hypsometric binning of DEM.

    Apart from doing the hypsometric binning, this function also creates a scatter plot of
    elevation differences, and results of the hypsometric binning. Maybe I should think about
    moving this to a different function.

    Parameters
    ----------
    - data-path
        path to IS2 dataset containing dh and dem_elevation variables

    Results
    -------
    Pandas dataframe of elevation bins.
    """

    # open dataset with xarray
    data = xr.open_dataset(data_path) # ICESat-2 data

    # replace no data values with nan
    data = data.where(data.dem_elevation < 2000)

    # plot elevation differences, size and color based on amount of difference
    scatter = plt.scatter(data.easting, data.northing, s=data.dh.where(data.dh>-20), c=data.dh, cmap="seismic")
    plt.legend(*scatter.legend_elements(), loc="lower left", title="Classes")
    plt.show()

    # hypsometric binning (ddem = elevation change, ref_dem = elevation from DEM)
    hypso = xdem.volume.hypsometric_binning(ddem=data["dh"], ref_dem=data["dem_elevation"], kind="quantile", bins=10)

    # plot binned data
    plt.plot(hypso["value"], hypso.index.mid)
    plt.show()

    return hypso

if __name__ == "__main__":
    main()
