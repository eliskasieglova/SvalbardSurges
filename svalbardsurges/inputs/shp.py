import geopandas as gpd
from pathlib import Path
import os
import socket

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

from pyproj import Proj


def load_shp(file_path, id_attribute, glacier_id):
    """
    Loads a single glacier as shapefile from the GAO dataset.

    Parameters
    ----------
    - file_path
        path to shapefile

    Returns
    -------
    Returns .shp of selected glacier.
    """

    filepath = Path(file_path)
    output_file = Path(f'cache/shapefiles/{glacier_id}.shp')

    # if glacier outline is cached simply load the shapefile
    if output_file.is_file():
        # todo handle when shapefile is empty (cannot read)
        glacier_outline = gpd.read_file(output_file).to_crs(32633)
        return glacier_outline

    # load glacier area outlines converted to EPSG:32633
    shp = gpd.read_file(file_path).to_crs(32633)

    # subset by chosen glacier ID (different for gao and rgi because of different id attribute format: str vs. float)
    if filepath.stem == 'gao':
        glacier_outline = shp.query(f"{id_attribute}=={glacier_id}")

    elif filepath.stem == 'rgi':
        glacier_outline = shp.query(f"{id_attribute}=='{glacier_id}'")

    # save as shp
    glacier_outline.to_file(filename=output_file)

    return glacier_outline


def withinBBox(bbox, filepath, id_attr, output_file):

    # if glacier outline is cached simply load the shapefile and return ids
    if output_file.is_file():
        shp = gpd.read_file(output_file).to_crs(32633)

        glacier_ids = []
        for index, row in shp.iterrows():
            if (row['geometry'].area / 1e6 > 15) & (row['glac_name'] != "None"):
                glacier_ids.append(row['glims_id'])

        return glacier_ids

    else:
        # read shapefile
        shp = gpd.read_file(filepath).to_crs(32633)

        # convert bbox lat lon to easting northing
        myproj = Proj("+proj=utm +zone=33 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")  # assign projection
        eastings, northings = myproj((bbox[0], bbox[2]), (bbox[1], bbox[3]))

        # select glaciers within bounding box
        from shapely.geometry import Polygon
        #polygon = Polygon([(bbox[0], bbox[1]), (bbox[2], bbox[1]), (bbox[2], bbox[3]), (bbox[0], bbox[3])])
        subset = shp.cx[eastings[0]:eastings[1], northings[0]:northings[1]]

        glacier_ids = []
        for index, row in shp.iterrows():
            if (row['geometry'].area / 1e6 > 15) & (row['glac_name'] != "None"):
                glacier_ids.append(row['glims_id'])

        # cache subset
        subset.to_file(filename=output_file)

        return glacier_ids
