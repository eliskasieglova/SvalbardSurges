from pathlib import Path
import geopandas as gpd


def load_shp(glacier_ident):
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

    # filter by glacier IDENT
    gao_glacier = gao.query(f"IDENT=={glacier_ident}")

    return gao_glacier