from pathlib import Path
import geoutils as gu
import rasterio as rio
import variete
import variete.vrt.vrt
import warnings
import svalbardsurges.paths as paths
from zipfile import ZipFile

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
        a label to assign when caching the result (name of glacier)

    Returns
    -------
    A subset of the DEM within the given bounds.
    """

    # paths
    file_path = Path('cache/NP_S0_DTM5_2011_25163_33/S0_DTM5_2011_25163_33.tif')
    vrt_warped_filepath = Path(f"cache/{file_path.stem}_{label}_warped.vrt")
    vrt_cropped_filepath = Path(f"cache/{file_path.stem}_{label}_cropped.vrt")

    # if subset does not exist create vrt
    if not vrt_cropped_filepath.is_file():
        # extract zipped file
        with ZipFile('cache/dem.zip') as zObject:
            zObject.extractall(Path('cache/'))

        # convert bounds (dict) to bounding box (list)
        bbox = rio.coords.BoundingBox(**bounds)

        # warp vrt (virtual raster), dst coord system EPSG:32633 (WGS-84)
        variete.vrt.vrt.vrt_warp(vrt_warped_filepath, file_path, dst_crs=32633)

        # crop warped vrt to bbox
        variete.vrt.vrt.build_vrt(vrt_cropped_filepath, vrt_warped_filepath, output_bounds=bbox)

    return vrt_cropped_filepath

def mask_dem(dem_path, gao, label) -> Path:
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

    path = Path(f'cache/{paths.dem_filename}')

    #if path.is_file():
     #   return path

    dem = xdem.DEM(str(dem_path), load_data=False)

    # rasterize the shapefile to fit the DEM
    gao_rasterized = gu.Vector(gao).create_mask(dem)

    # extract values inside the glacier area outlines
    dem.load()
    dem.set_mask(~gao_rasterized)

    dem.save(str(path))

    return path