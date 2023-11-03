from pathlib import Path
import os
import socket

if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

from pyproj import CRS

import warnings
# Catch a deprecation warning that arises from skgstat when importing xdem
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem

import geopandas as gpd
import rasterio as rio
import rasterio.features
import rasterio.warp
import os
import geoutils as gu
import numpy as np
from tqdm import tqdm
import shapely.geometry
from zipfile import ZipFile

from svalbardsurges import download

def align_bounds(
    bounds: rio.coords.BoundingBox | dict[str, float],
    res: tuple[float, float] | None = None,
    half_mod: bool = False,
    buffer: float | None = None,
) -> rio.coords.BoundingBox:
    if isinstance(bounds, rio.coords.BoundingBox):
        bounds = {key: getattr(bounds, key) for key in ["left", "bottom", "right", "top"]}

    if res is None:
        res = (5.0, 5.0)
    # Ensure that the moduli of the bounds are zero
    for i, bound0 in enumerate([["left", "right"], ["bottom", "top"]]):
        for j, bound in enumerate(bound0):

            mod = (bounds[bound] - (res[i] / 2 if half_mod else 0)) % res[i]

            bounds[bound] = (
                bounds[bound] - mod + (res[i] if i > 0 and mod != 0 else 0) + ((buffer or 0) * (1 if i > 0 else -1))
            )

    return rio.coords.BoundingBox(**bounds)

def get_bounds(
    region: str = "heerland", res: tuple[float, float] | None = None, half_mod: bool = False
) -> rio.coords.BoundingBox:
    """
    Get the bounding coordinates of the output DEMs.

    Arguments
    ---------
    - region: The selected region (with hardcoded bounds)
    - res: Optional. Override the x/y resolution.
    - half_mod: Whether the modulus should be calculated on half the pixel size (e.g. 50000 at 5m -> 50002.5)

    Returns
    -------
    A bounding box of the region.
    """

    region_bounds = {
        "svalbard": {"left": 341002.5, "bottom": 8455002.5, "right": 905002.5, "top": 8982002.5},
        "nordenskiold": {"left": 443002.5, "bottom": 8626007.5, "right": 560242.5, "top": 8703007.5},
        "heerland": {"left": 537010, "bottom": 8602780, "right": 582940, "top": 8656400},
    }

    bounds = region_bounds[region]

    return align_bounds(bounds, res=res, half_mod=half_mod)

def get_data_urls():
    np_dem_base_url = "https://public.data.npolar.no/kartdata/S0_Terrengmodell/Delmodell/"

    data_dir = Path('cache/')

    urls = {
        "strip_metadata": [
            (
                "https://pgc-opendata-dems.s3.us-west-2.amazonaws.com/arcticdem/strips/s2s041/2m.json",
                "geocell_metadata.json",
            )
        ],
        "NP_DEMs": [
            np_dem_base_url + url
            for url in [
                "NP_S0_DTM5_2008_13652_33.zip",
                "NP_S0_DTM5_2008_13657_35.zip",
                "NP_S0_DTM5_2008_13659_33.zip",
                "NP_S0_DTM5_2008_13660_33.zip",
                "NP_S0_DTM5_2008_13666_35.zip",
                "NP_S0_DTM5_2008_13667_35.zip",
                "NP_S0_DTM5_2009_13822_33.zip",
                "NP_S0_DTM5_2009_13824_33.zip",
                "NP_S0_DTM5_2009_13827_35.zip",
                "NP_S0_DTM5_2009_13833_33.zip",
                "NP_S0_DTM5_2009_13835_33.zip",
                "NP_S0_DTM5_2010_13826_33.zip",
                "NP_S0_DTM5_2010_13828_33.zip",
                "NP_S0_DTM5_2010_13832_35.zip",
                "NP_S0_DTM5_2010_13836_33.zip",
                "NP_S0_DTM5_2010_13918_33.zip",
                "NP_S0_DTM5_2010_13920_35.zip",
                "NP_S0_DTM5_2010_13922_33.zip",
                "NP_S0_DTM5_2010_13923_33.zip",
                "NP_S0_DTM5_2011_13831_35.zip",
                "NP_S0_DTM5_2011_25160_33.zip",
                "NP_S0_DTM5_2011_25161_33.zip",
                "NP_S0_DTM5_2011_25162_33.zip",
                "NP_S0_DTM5_2011_25163_33.zip",
                "NP_S0_DTM5_2012_25235_33.zip",
                "NP_S0_DTM5_2012_25236_35.zip",
                "NP_S0_DTM5_2021_33.zip",
            ]
        ],
        "outlines": [
            "https://public.data.npolar.no/kartdata/NP_S100_SHP.zip",
            (
                "https://api.npolar.no/dataset/"
                + "f6afca5c-6c95-4345-9e52-cfe2f24c7078/_file/3df9512e5a73841b1a23c38cf4e815e3",
                "GAO_SfM_1936_1938.zip",
            ),
        ],
    }

    for key in urls:
        for i, entry in enumerate(urls[key]):
            if isinstance(entry, tuple):
                filename = entry[1]
                url = entry[0]
            else:
                filename = os.path.basename(entry)
                url = entry

            urls[key][i] = (url, data_dir.joinpath(key).joinpath(filename))

    return urls

def build_npi_mosaic(verbose: bool = True) -> tuple[Path, Path]:
    """
    Build a mosaic of tiles downloaded from the NPI.

    Arguments
    ---------
    - verbose: Whether to print updates to the console

    Returns
    -------
    A path to the NPI mosaic.
    """

    bounds = get_bounds()
    data_dir = Path('cache/NP_DEMs')
    temp_dir = Path('cache/')

    output_path = Path("data/npi_mosaic_clip.tif")
    output_year_path = Path("data/npi_mosaic_clip_years.tif")

    if output_path.is_file() and output_year_path.is_file():
        return output_path, output_year_path

    from osgeo import gdal

    crs = CRS.from_epsg(32633)
    res = (5.0, 5.0)

    bounds_epsg25833 = shapely.geometry.box(
        *gpd.GeoSeries([shapely.geometry.box(*bounds)], crs=32633).to_crs(25833).buffer(50).total_bounds)

    # Generate links to the DEM tiles within their zipfiles
    uris = []
    year_rasters = []
    for url, filepath in tqdm(get_data_urls()["NP_DEMs"], desc="Preparing DEMs and year info", disable=(not verbose)):
        year = int(filepath.stem.split("_")[3])

        if not filepath.is_file():
            filepath.parent.mkdir(parents=True, exist_ok=True)
            download.download_file(url, directory='cache/NP_DEMs')

            with ZipFile(filepath) as zObject:
                zObject.extractall(Path('cache/NP_DEMs/'))

        uri = f"cache/NP_DEMs/{str(filepath.stem)}/{str(filepath.stem.replace('NP_', ''))}.tif"

        dem = xdem.DEM(uri, load_data=False)

        dem_bbox = shapely.geometry.box(*dem.bounds)
        if not bounds_epsg25833.overlaps(dem_bbox):
            continue

        dem.crop(bounds_epsg25833.bounds)

        year_raster = gu.Raster.from_array(
            (np.zeros(dem.shape, dtype="uint16") + year) * (1 - dem.data.mask.astype("uint16")),
            transform=dem.transform,
            crs=dem.crs,
            nodata=0,
        )

        year_rasters.append(year_raster)
        uris.append(uri)

    if verbose:
        print("Merging rasters")

    year_raster = gu.raster.merge_rasters(year_rasters, merge_algorithm=np.nanmax, resampling_method="nearest")

    year_raster.reproject(dst_bounds=bounds, dst_res=res, dst_crs=crs, resampling="nearest").save(
        output_year_path, tiled=True, compress="lzw"
    )
    del year_raster

    vrt_dir = temp_dir.joinpath("npi_vrts/")
    vrt_dir.mkdir(exist_ok=True)
    mosaic_path = vrt_dir.joinpath("npi_mosaic.vrt")

    # Mosaic the tiles in a VRT
    gdal.BuildVRT(str(mosaic_path), uris)

    if verbose:
        print("Saving DEM mosaic")
    # Warp the VRT into one TIF
    gdal.Warp(
        str(output_path),
        str(mosaic_path),
        dstSRS=crs.to_wkt(),
        creationOptions=[f"{k}={v}" for k, v in {"COMPRESS": "DEFLATE", "ZLEVEL": "12", "TILED": "YES", "NUM_THREADS": "ALL_CPUS"}.items()],
        xRes=res[0],
        yRes=res[1],
        resampleAlg=rasterio.warp.Resampling.cubic_spline,
        outputBounds=list(bounds),
        multithread=True,
    )

    if verbose:
        print('Mosaic saved.')
    return output_path