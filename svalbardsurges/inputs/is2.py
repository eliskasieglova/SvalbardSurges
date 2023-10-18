import xarray as xr
from pathlib import Path
import geopandas as gpd


def subset_is2(input_path, bounds, glacier_outline, output_path):
    """
    Subset IS2 data using specified bounds and shapefile.

    The easting and northing variables need to be loaded in memory, so this is a computationally expensive task.
    The function is cached using the label argument to speed up later calls.

    Parameters
    ----------
    - input_path
        path to the ICESat-2 data
    - bounds
        bounding box to use (requires the keys: "left", "right", "bottom", "top")
    - glacier_outline
        glacier outline as .shp
    - output_path


    Returns
    -------
    Path to the subset of IS2 dataset within the given glacier area.
    """

    # if subset already exists return path
    if output_path.is_file():
        return output_path

    # load data
    data = xr.open_dataset(input_path)

    # crop data by bounds
    subset = data.where(
        (data.easting > bounds["left"]) & (data.easting < bounds["right"]) & (data.northing > bounds["bottom"]) & (
                    data.northing < bounds["top"]), drop=True)

    # create geometry from IS2 points
    points = gpd.points_from_xy(x=subset.easting, y=subset.northing)

    # points within shapefile
    inlier_mask = points.within(glacier_outline.iloc[0].geometry)

    # create subset of IS2 clipped by glacier area
    subset = subset.where(xr.DataArray(inlier_mask, coords=subset.coords), drop=True)

    # save file
    output_path.parent.mkdir(exist_ok = True)
    subset.to_netcdf(output_path)

    return output_path