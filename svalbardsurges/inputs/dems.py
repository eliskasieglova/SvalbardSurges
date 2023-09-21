from pathlib import Path
import geoutils as gu
import rasterio as rio
import variete
import variete.vrt.vrt
import warnings

# Catch a deprecation warning that arises from skgstat when importing xdem
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem

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

    # rasterize the shapefile to fit the DEM
    gao_rasterized = gu.Vector(gao).create_mask(dem)

    # extract values inside the glacier area outlines
    dem.load()
    dem.set_mask(~gao_rasterized)

    return dem