from pathlib import Path
import geopandas as gpd
import svalbardsurges.paths as paths


def load_shp(glacier_id):
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

    # load shapefile of glacier area outlines converted to EPSG:32633
    file_path = Path(f'cache/gao.zip')
    gao = gpd.read_file(file_path).to_crs(32633)

    # subset by chosen glacier ID
    glacier_outline = gao.query(f"IDENT=={glacier_id}")

    return glacier_outline