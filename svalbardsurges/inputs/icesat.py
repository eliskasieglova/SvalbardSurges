import xarray as xr
import geopandas as gpd
import icepyx as ipx
import numpy as np
import h5py
import os
import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point
import cartopy.crs as ccrs
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
import statistics as stat
from scipy import stats
from scipy.stats import norm

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

    bins = [-200, 0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100, 1200]
    plt.figure(figsize=(10, 10))
    plt.style.use('seaborn-v0_8-darkgrid')
    plt.hist(data, bins=bins)
    plt.show()

    return st

def readIS2_icepyx(input_path, data_product, output_path):

    # pattern for naming files
    pattern = "processed_ATL{product:2}_{datetime:%Y%m%d%H%M%S}_{rgt:4}{cycle:2}{orbitsegment:2}_{version:3}_{revision:2}.h5"

    # create an icepyx read object
    reader = ipx.Read(data_source=str(input_path), product=data_product, filename_pattern=pattern)

    if data_product == 'ATL03':
        reader.vars.append(var_list=["h_ph", "lat_ph", "lon_ph"])

    if data_product == 'ATL06':
        # select variables
        reader.vars.append(var_list=["h_li", "latitude", "longitude"])

    if data_product == 'ATL08':
        reader.vars.append(var_list=["h_te_best_fit", "latitude", "longitude"])

    reader.vars.wanted

    ds = reader.load()
    print(ds)

    # save data as netcdf
    ds.to_netcdf(output_path)

    return ds

def subset_is2(input_path, spatial_extent, glacier_outline, output_path):
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
        (data.longitude > spatial_extent["left"]) & (data.longitude < spatial_extent["right"]) & (data.latitude > spatial_extent["bottom"]) & (
                    data.latitude < spatial_extent["top"]), drop=True)

    # create geometry from IS2 points
    points = gpd.points_from_xy(x=subset.longitude, y=subset.latitude)

    # points within shapefile
    inlier_mask = points.within(glacier_outline.iloc[0].geometry)

    # create subset of IS2 clipped by glacier area
    subset = subset.where(xr.DataArray(inlier_mask, coords=subset.coords), drop=True)

    # save file
    output_path.parent.mkdir(exist_ok = True)
    subset.to_netcdf(output_path)

    return output_path

# READING ICESAT-2 DATA
# functions from Desiree adapted to xarray outputs
# https://github.com/desireetreichler/snowdepth/blob/main/tools/IC2tools.py
# ---------------------------------------------------

def ATL08_to_dict(filename, dataset_dict):
    """
        Read selected datasets from an ATL06 file
        Input arguments:
            filename: ATl08 file to read
            dataset_dict: A dictinary describing the fields to be read
                    keys give the group names to be read,
                    entries are lists of datasets within the groups
        Output argument:
            D6: dictionary containing ATL08 data.  Each dataset in
                dataset_dict has its own entry in D6.  Each dataset
                in D6 contains a list of numpy arrays containing the
                data
    """

    D6 = []
    pairs = [1, 2, 3]
    beams = ['l', 'r']
    # open the HDF5 file
    with h5py.File(filename, 'r') as h5f:  # added mode to 'r', to suppress depreciation warning
        # loop over beam pairs
        for pair in pairs:
            # loop over beams
            for beam_ind, beam in enumerate(beams):
                # check if a beam exists, if not, skip it
                if '/gt%d%s/land_segments' % (pair, beam) not in h5f:
                    continue
                # loop over the groups in the dataset dictionary
                temp = {}
                for group in dataset_dict.keys():
                    for dataset in dataset_dict[group]:
                        DS = '/gt%d%s/%s/%s' % (pair, beam, group, dataset)
                        # since a dataset may not exist in a file, we're going to try to read it, and if it doesn't work, we'll move on to the next:
                        try:
                            temp[dataset] = np.array(h5f[DS])
                            # some parameters have a _FillValue attribute.  If it exists, use it to identify bad values, and set them to np.NaN
                            if '_FillValue' in h5f[DS].attrs:
                                fill_value = h5f[DS].attrs['_FillValue']
                                bad = temp[dataset] == fill_value
                                try:
                                    temp[dataset] = np.float64(temp[dataset])
                                    temp[dataset][bad] = np.NaN
                                except TypeError:  # as e: # added this exception, as I got some type errors - temp[dataset] was 0.0
                                    pass
                            # a few attributes have 5 columns, corresponding to either 30m segments or land, ocean, sea ice, land ice, inland water
                            try:
                                if len(temp[dataset][0] == 5):
                                    if dataset in ['h_te_best_fit_20m']:
                                        for segnr, segstr in enumerate(['1', '2', '3', '4', '5']):
                                            temp[dataset + '_' + segstr] = temp[dataset][:, segnr]
                                        del temp[dataset]
                                    else:  # default = land, first column
                                        for surftypenr, surftype in enumerate(
                                                ['ocean', 'seaice', 'landice', 'inlandwater']):
                                            temp[dataset + '_' + surftype] = temp[dataset][:, surftypenr + 1]
                                        temp[dataset] = temp[dataset][:, 0]
                            except TypeError:  # as e: # added this exception, as I got some type errors - temp[dataset] was 0.0
                                pass
                            except IndexError:  # as e: # added this exception, as I got some *** IndexError: invalid index to scalar variable.
                                pass
                        except KeyError:  # as e:
                            pass
                if len(temp) > 0:
                    # it's sometimes convenient to have the beam and the pair as part of the output data structure: This is how we put them there.
                    # a = np.zeros_like(temp['h_te_best_fit'])
                    # print(a)
                    temp['pair'] = np.zeros_like(temp['h_te_best_fit']) + pair
                    temp['beam'] = np.zeros_like(temp['h_te_best_fit']) + beam_ind
                    # RGT and cycle are also convenient. They are in the filename.
                    fs = filename.split('_')
                    temp['RGT'] = np.zeros_like(temp['h_te_best_fit']) + int(fs[-3][0:4])
                    temp['cycle'] = np.zeros_like(temp['h_te_best_fit']) + int(fs[-3][4:6])
                    # temp['filename']=filename
                    D6.append(temp)
    return D6

def point_convert(row):
    geom = Point(row['longitude'], row['latitude'])
    return geom

def ATL08_to_gdf(dataset_path, dataset_dict):
    """
    based on Desiree's ATL08_2_gdf().
    converts ATL06 hdf5 to xarray dataset.

    Params
    ------
    - dataset_path
        directory with ATL08 hdf5 files.
    - dataset_dict
        dictionary of wanted variables to read from hdf5 file

    Returns
    -------
    merged xarray dataset.
    """

    if ('latitude' in dataset_dict['land_segments']) != True:
        dataset_dict['land_segments'].append('latitude')
    if ('longitude' in dataset_dict['land_segments']) != True:
        dataset_dict['land_segments'].append('longitude')

    data_dict = ATL08_to_dict(dataset_path, dataset_dict)
    # this will give us 6 tracks
    i = 0
    for track in data_dict:
        # 1 track
        # convert to dataframe
        df = pd.DataFrame(track)
        try:
            df['pb'] = df['pair'] * 10 + df['beam']
            # df['p_b'] = str(track['pair'][0])+'_'+str(track['beam'][0])
        except:  # added, to account for errors - maybe where there is only one data point (?)
            df['pb'] = track['pair'] * 10 + track['beam']
            # df['p_b'] = str(track['pair'])+'_'+str(track['beam'])

        #df['geometry'] = df.apply(point_convert, axis=1)
        if i == 0:
            df_final = df.copy()
        else:
            df_final = pd.concat((df_final, df))
        i = i + 1
    #pd_final = gpd.GeoDataFrame(df_final, geometry='geometry', crs='epsg:32633')  # changed from +init-version to avoid the upcoming warning
    pd_final = gpd.GeoDataFrame(df_final)

    return pd_final

def concat_xr(gdf_list, dataproduct):
    """
    from Desiree

    concatanate geodataframes into 1 geodataframe
    Assumes all input geodataframes have same projection
    Inputs : list of geodataframes in same projection
    Output : 1 geodataframe containing everything having the same projection
    """
    #from https://stackoverflow.com/questions/48874113/concat-multiple-shapefiles-via-geopandas
    gdf = pd.concat([gdf for gdf in gdf_list]).pipe(gpd.GeoDataFrame)
    try:
        gdf.crs = (gdf_list[0].crs)
        if gdf.crs is None:
            gdf.crs='epsg:32633'  # sometimes the first geodataframe in a list may be empty, causing the result not to have a coordinate system.
    except:
        print('Warning: no CRS assigned')
        pass

    ds = gdf.to_xarray()
    ds.to_netcdf(f'data/icesat_{dataproduct}.nc')

def ATL08_to_xr(input_path, output_path):
    """
    function putting together the process of converting ATL08 hdf5 data to an xarray dataset
    using functions from Desiree

    Params
    ------
    - input_path
        path pointing to the directory where ATL08 hdf5 files are saved
    - output_path
        where the xarray dataset should be stored (as netcdf), including filename

    Returns
    -------
    path pointing to the output netcdf file
    """

    if output_path.is_file():
        return output_path

    # dictionary of variables we want in out final xarray dataset according to the ATL08 product dictionary
    # https://icesat-2-scf.gsfc.nasa.gov/sites/default/files/asas/asasv60/atl08_template.html

    datadict = {
        'land_segments' : ['latitude', 'longitude'],
        'land_segments/terrain': ['h_te_best_fit']
    }

    gdf_list = []
    for file in os.listdir(input_path):
        ds = ATL08_to_gdf(f'{input_path}/{file}', datadict)
        gdf_list.append(ds)

    concat_xr(gdf_list, 'ATL08')

    return output_path










# FUNCTIONS I WORKED ON BUT MOST LIKELY WILL NOT NEED
# ---------------------------------------------------

def h5_to_netcdf(dir):
    """
    Load ICESat-2 data using h5py.

    Params:
    ------
    FILE_NAME
        file name of h5 file to directory where ICESat-2 files are saved

    Returns:
    -------
    Path to saved netcdf file.
    """
    # empty dictionary
    ds = {}

    # open file
    for file in os.listdir(dir):
        with h5py.File(f'cache/is2_ATL08/{file}', mode='r') as f:

            beams = ['/gt1l/', '/gt2l/', '/gt3l/', '/gt1r/', '/gt2r/', '/gt3r/']
            vars = [
                ('lat', 'land_segments/latitude'),
                ('lon', 'land_segments/longitude'),
                ('brightness_flag', 'land_segments/brightness_flag'),
                ('cloud_flag_atm', 'land_segments/cloud_flag_atm'),
                ('dem_h', 'land_segments/dem_h'),
                ('dem_flag', 'land_segments/dem_flag'),
                ('h_te_best_fit', 'land_segments/terrain/h_te_best_fit'),
            ]

            # append date
            ds['date'] = f['ancillary_data/data_start_utc'][:]

            i = 0
            for beam in beams:
                for var in vars:
                    if i == 0:
                        # if loop running for the first time create variables in dataset
                        ds[str(f'{var[0]}_{beam[1:-1]}')] = f[f'{beam}{var[1]}'][:]
                    else:
                        np.append(ds[str(f'{var[0]}_{beam[1:-1]}')], f[f'{beam}{var[1]}'][:])

            i = 1
            f.close()

    return