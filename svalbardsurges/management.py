import os
from user_vars import label
import geopandas as gpd
from pathlib import Path


def createDirs():
    """
    Create the necessary structure of directories for this code to work.
    """

    createFolder('data/')
    createFolder('data/raw')
    createFolder('temp/')
    createFolder('temp/glaciers/')
    createFolder('results/')
    createFolder('figs/')


def createFolder(path):
    """create new folder"""

    # check if folder already exists
    if not os.path.exists(path):
        # if not, make folder
        os.mkdir(path)

    return


def listGlacierIDs(glaciers):
    """
    Lists glacier IDs that are inside the bbox of the area of interest.

    :param glaciers: df/gdf of glaciers from RGI based on the selected area

    :return: list of glacier IDs
    """
    glacier_ids = []

    for i in range(len(glaciers)):
        row = glaciers.iloc[i]
        glacier_id = row['glims_id']
        glacier_ids.append(glacier_id)

    return glacier_ids


def loadGlacierShapefile(glacier_id):
    outpath = Path(f'temp/glaciers/{glacier_id}.gpkg')

    # cache
    if outpath.is_file():
        return gpd.read_file(outpath)

    # load the RGI shapefile
    rgi = gpd.read_file(f'data/rgi_{label}.gpkg')

    # select glacier with input glacier_id
    glacier = rgi[rgi['glims_id'] == glacier_id]

    # save this glacier
    glacier.to_file(outpath)

    return glacier

