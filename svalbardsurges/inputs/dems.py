from pathlib import Path
import geoutils as gu
import rasterio as rio
import variete
import variete.vrt.vrt

import os
from matplotlib import pyplot as plt
import numpy as np

import warnings
# Catch a deprecation warning that arises from skgstat when importing xdem
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem

def load_dem(input_path, bounds, label):
    """
    Loads subset of DEM using the specified bounds.

    Working with the DEM as a vrt.

    Parameters
    ----------
    - bounds
        the bounding box to use (requires the keys "left", "right", "bottom", "top")
    - label
        a label to assign when caching the result (name of glacier)

    Returns
    -------
    Path to the subset of the DEM within the given bounds.
    """

    # paths
    vrt_warped_filepath = Path(f"cache/{label}_warped.vrt")
    vrt_cropped_filepath = Path(f"cache/{label}_cropped.vrt")

    # if subset does not exist create vrt
    if not vrt_cropped_filepath.is_file():

        # convert bounds (dict) to bounding box (list)
        bbox = rio.coords.BoundingBox(**bounds)

        # warp vrt (virtual raster), dst coord system EPSG:32633 (WGS-84)
        variete.vrt.vrt.vrt_warp(vrt_warped_filepath, input_path, dst_crs=32633)

        # crop warped vrt to bbox
        variete.vrt.vrt.build_vrt(vrt_cropped_filepath, vrt_warped_filepath, output_bounds=bbox)

    return vrt_cropped_filepath

def mask_dem(dem_path, glacier_outline, label) -> Path:
    """
    Masks DEM data by the glacier area outlines.

    Parameters
    ----------
    -dem
        path to DEM we want to mask
    - gao
        glacier area outline as input for masking the DEM (as .shp)

    Returns
    -------
    Masked DEM containing values only within the glacier area outlines.
    """

    path = Path(f'cache/{label}_masked.tif')
    if path.is_file():
        return path

    # create DEM from .vrt
    dem = xdem.DEM(str(dem_path), load_data=False)

    # rasterize the shapefile to fit the DEM
    gao_rasterized = gu.Vector(glacier_outline).create_mask(dem)

    # extract values inside the glacier area outlines
    dem.load()
    dem.set_mask(~gao_rasterized)

    dem.save(str(path))

    return path

def validate(arcticDEM_directory, ref_dem_path, bounds, glacier_outline, output_name):
    """
    Validate results of IS2 data using ArcticDEM.

    """

    # cache
    if output_name.is_file():
        return output_name

    dems = {}

    ref_dem = xdem.DEM(load_dem(ref_dem_path, bounds=bounds, label=f"ref_dem-{glacier_outline.NAME.iloc[0]}"))
    gao_rasterized = gu.Vector(glacier_outline).create_mask(ref_dem)
    # extract values inside the glacier area outlines
    ref_dem.set_mask(~gao_rasterized)

    bins = np.nanpercentile(ref_dem.data.filled(np.nan), np.linspace(0, 100, 6))
    bins[-1] *= 1.1

    # load VRTs of ArcticDEM cropped by glacier outline
    for file in os.listdir(arcticDEM_directory):
        # extract year from file name
        year = file[11:-4]

        # load vrt of DEM cropped to bounds
        dem_path = load_dem(arcticDEM_directory/file, bounds, f'arcticdem{year}_{glacier_outline.NAME.iloc[0]}')

        dems[year] = dem_path
        continue
        # crop to glacier outline
        dem_masked = mask_dem(dem_path, glacier_outline, f'arcticdem{year}_{glacier_outline.NAME.iloc[0]}')

        # append to dictionary
        dems[year] = dem_masked

    # cache
    output_name = Path(f'figures/{glacier_outline.IDENT.iloc[0]}_adem_hypso.png')

    if output_name.is_file():
        return

    # plot elevation differences
    for year in dems:
        year = int(year)

        dem1 = xdem.DEM(str(dems[str(year)])).reproject(ref_dem)
        dem_difference = dem1 - ref_dem

        plt.figure()
        plt.title(f'{glacier_outline.NAME.iloc[0]}({glacier_outline.IDENT.iloc[0]}), {year + 1}')

        dem_difference.show(vmin=-50, vmax=50, cmap='seismic_r')
        plt.savefig(f'figures/{glacier_outline.IDENT.iloc[0]}_arcticdem_{year}.png')
        plt.close()

    n = 1
    plt.subplots(2, 3, sharey=True, sharex=True)
    plt.suptitle(f'{glacier_outline.NAME.iloc[0]} (ArcticDEM)', fontsize=16)

    for year in dems:
        year = int(year)
        dem1 = xdem.DEM(str(dems[str(year)])).reproject(ref_dem)

        dem_difference = dem1 - ref_dem

        # create hypsometric binning
        if np.count_nonzero(np.isfinite(dem_difference.data.filled(np.nan))) == 0:
            continue
        hypso = xdem.volume.hypsometric_binning(ddem=dem_difference.data, ref_dem=dem1.data, kind='custom', bins=bins)

        plt.subplot(2,3,n)
        plt.title(f'2010-{year}')
        plt.plot(hypso['value'], hypso.index.mid)
        plt.xlim(-40,40)
        n = n+1

    plt.savefig(f'figures/{glacier_outline.IDENT.iloc[0]}_arcticdem_hypso.png')
    plt.close()


    return


