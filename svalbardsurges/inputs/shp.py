from pathlib import Path
import geopandas as gpd
from svalbardsurges import paths


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

    # load shapefile of glacier area outlines converted to EPSG:32633
    shp = gpd.read_file(file_path).to_crs(32633)

    # subset by chosen glacier ID
    glacier_outline = shp.query(f"{id_attribute_name}=='{glacier_id}'")

    return glacier_outline