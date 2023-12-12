import geopandas as gpd
import xarray as xr
import matplotlib.pyplot as plt
import statistics as stat
import socket
import os
from pathlib import Path
import numpy as np

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"


def statistics(data_path = 'nordenskiold_land-is2.nc'):

    ds = xr.open_dataset(data_path)
    data = ds['h_te_best_fit'].values
    st = {
        'min': min(data),
        'max': max(data),
        'mean': stat.mean(data),
        'median': stat.median(data),
        'stdev': stat.stdev(data)
    }

    print(st)

    bins = [-200, 0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200]
    plt.figure(figsize=(10, 10))
    plt.style.use('seaborn-v0_8-darkgrid')
    plt.hist(data, bins=bins)
    plt.show()

    return st


def icesatSpatialSubset(input_path, spatial_extent, glacier_outline, output_path):
    """
    Subset IS2 data using specified bounds and shapefile.

    The easting and northing variables need to be loaded in memory, so this is a computationally expensive task.
    The function is cached using the label argument to speed up later calls.

    Parameters
    ----------
    - input_path
        path to the ICESat-2 data
    - spatial_extent
        bounding box to use (requires the keys: "left", "bottom", "right", "top")
    - glacier_outline
        glacier outline as .shp
    - output_path


    Returns
    -------
    Path to the subset of IS2 dataset within the given glacier area.
    """

    # if subset already exists return path
    if output_path.is_file():
        subset = xr.open_dataset(output_path)
        return subset

    # load data
    data = xr.open_dataset(input_path, decode_coords=False)

    #if input_path == Path('nordenskiold_land-is2.nc'):
    #    for b in ['', '_20m_0', '_20m_1', '_20m_2', '_20m_3', '_20m_4']:
    #        data[f'h{b}'] = data[f'h_te_best_fit{b}']

    #    from matplotlib import pyplot as plt
    #    plt.scatter(data.easting, data.northing)
    #    plt.plot([spatial_extent['left'], spatial_extent['right'], spatial_extent['right'], spatial_extent['left']],
    #             [spatial_extent['bottom'], spatial_extent['bottom'], spatial_extent['top'], spatial_extent['top']])
    #    plt.show()

    # clip data to bounding box
    try:
        subset = data.where(
            (data.easting > spatial_extent["left"]) & (data.easting < spatial_extent["right"]) & (data.northing > spatial_extent["bottom"]) & (
                        data.northing < spatial_extent["top"]), drop=True)
    except:
        data.load()
        subset = data.where(
            (data.easting > spatial_extent["left"]) & (data.easting < spatial_extent["right"]) & (
                        data.northing > spatial_extent["bottom"]) & (
                    data.northing < spatial_extent["top"]), drop=True)

    # if subset is empty all the analysis, plotting and validation will be set to False in main.py
    # todo better way of filtering
    if subset.index.size < 20:
        return 'empty'

    # clip data to glacier outline (shapefile)
    points = gpd.points_from_xy(x=subset.easting, y=subset.northing)  # create geometry from ICESat-2 points
    inlier_mask = points.within(glacier_outline.iloc[0].geometry)  # points within shapefile
    subset = subset.where(xr.DataArray(inlier_mask, coords=subset.coords), drop=True)  # subset xarray dataset

    if subset.index.size == 0:
        return 'empty'

    # save file
    output_path.parent.mkdir(exist_ok = True)
    try:
        subset = subset.drop_vars('date_str')  # todo move this to the whole dh
    except:
        subset = subset


    subset.to_netcdf(output_path)

    return subset


def fillWithNans(df, year, glacier_id, bins, name, geom):

    # name and geometry
    df["name"].loc[{"glacier_id": glacier_id}] = name
    df["geom"].loc[{"glacier_id": glacier_id}] = geom

    # nan values
    df["max_dh"].loc[{"year": year, "glacier_id": glacier_id}] = np.nan
    df["slope"].loc[{"year": year, "glacier_id": glacier_id}] = np.nan
    df["intercept"].loc[{"year": year, "glacier_id": glacier_id}] = np.nan
    df["bin_max"].loc[{"year": year, "glacier_id": glacier_id}] = np.nan
    df["surging"].loc[{"year": year, "glacier_id": glacier_id}] = False

    # bins
    #for i in range(0, len(bins) - 1):
    #    df["avg_dh"].loc[{"year": year, "glacier_id": glacier_id, "bin": bins[i + 1]}] = np.nan
    #    df["count"].loc[{"year": year, "glacier_id": glacier_id, "bin": bins[i + 1]}] = np.nan

    return df



def yearsInData(input_path):
    # cache
    output_path = Path(f'data/icesat.nc')
    if output_path.is_file():
        data = xr.open_dataset(output_path)
        # how many years
        years = np.unique(data.year_int.values)
        return output_path, years

    # open dataset
    data = xr.open_dataset(input_path)

    # save date in int format as variable
    data['date_str'] = ('index', data.date.values.astype(str))
    data['date_int'] = ('index', [int(x[:10].replace('-', '')) for x in data.date_str.values])
    data['year_int'] = ('index', [int(x[:4]) for x in data.date_str.values])

    # how many years
    years = np.unique(data.year_int.values)

    # save data
    data.to_netcdf(output_path)

    return output_path, years

    return output_path


def groupby_hydroyear(data, year):
    """
    Creates a subset of ICESat-2 data (xarray) based on split date (defaults to hydrological year).

    Params
    ------
    - data
        xarray dataset
    - year
        int, format yyyy
    - splitday
        day at which i want to split year, int, format mmdd (defaults to 1031 = october 31st, hydrological new year)

    Returns
    -------
    Subset of former dataset split by hydrological year (if splitday == 1031)
    """

    # create hydrosilvestr (31st october) for given year as in in yyymmdd
    hydrosilvestr = year * 10000 + 1031

    # create subset of data
    subset = data.where((data.date_int.values > hydrosilvestr-10000) & (data.date_int.values <= hydrosilvestr + 10000))
    subset = subset.dropna('index')

    return subset

def icesatVarSubset(icesat_path):

    data = xr.load_dataset(icesat_path)

    subset = data.drop_vars()


    return subset