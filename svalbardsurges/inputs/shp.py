import geopandas as gpd
from pathlib import Path
import os
import socket

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

from pyproj import Proj


def getIDs(filepath, id_attr):
    """
    Loops through entries in shp and extracts glacier IDs to a list.

    Params
    ------
    - filepath
        path to rgi or gao

    Returns
    -------
    list of glacier ids
    """

    # load shapefile
    shp = gpd.read_file(filepath).to_crs(32633)

    glacier_ids = []
    for i in shp[id_attr]:
        glacier_ids.append(i)

    return glacier_ids


def load_shp(file_path, id_attribute_name, glacier_id):
    """
    Loads a single glacier as shapefile from the GAO dataset.

    Parameters
    ----------
    - file_path
        path to shapefile
    - glacier name
        name of glacier we want to load as string

    Returns
    -------
    Returns .shp of selected glacier.
    """

    filepath = Path(file_path)
    output_file = Path(f'cache/shapefiles/{filepath.stem}_{glacier_id}.shp')

    # if glacier outline is cached simply load the shapefile
    if output_file.is_file():
        glacier_outline = gpd.read_file(output_file).to_crs(32633)
        return glacier_outline

    # if glacier outline is not cached, load it and save it

    # load glacier area outlines converted to EPSG:32633
    shp = gpd.read_file(file_path).to_crs(32633)

    # subset by chosen glacier ID (different for gao and rgi because of different id attribute format: str vs. float)
    if filepath.stem == 'gao':
        glacier_outline = shp.query(f"{id_attribute_name}=={glacier_id}")

    elif filepath.stem == 'rgi':
        glacier_outline = shp.query(f"{id_attribute_name}=='{glacier_id}'")

    # save as shp
    glacier_outline.to_file(filename=output_file)

    return glacier_outline

def withinBBox(bbox, filepath, output_file):

    # if glacier outline is cached simply load the shapefile
    if output_file.is_file():
        subset = gpd.read_file(output_file).to_crs(32633)
        return subset

    # read shapefile
    shp = gpd.read_file(filepath).to_crs(32633)

    # convert bbox lat lon to easting northing
    myproj = Proj("+proj=utm +zone=33 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")  # assign projection
    eastings, northings = myproj((bbox[0], bbox[2]), (bbox[1], bbox[3]))

    # select glaciers within bounding box
    subset = shp.cx[eastings[0]:eastings[1], northings[0]:northings[1]]

    # cache subset
    subset.to_file(filename=output_file)

    return subset
