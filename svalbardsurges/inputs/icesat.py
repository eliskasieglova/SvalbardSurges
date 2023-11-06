import geopandas as gpd
import icepyx as ipx
import numpy as np
import h5py
import xarray as xr
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point
import statistics as stat
from datetime import datetime
import socket
import os

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

from pyproj import Proj

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

def subset_icesat(input_path, spatial_extent, glacier_outline, output_path):
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
        return output_path

    # load data
    data = xr.open_dataset(input_path, decode_coords=False)

    # clip data to bounding box
    subset = data.where(
        (data.easting > spatial_extent["left"]) & (data.easting < spatial_extent["right"]) & (data.northing > spatial_extent["bottom"]) & (
                    data.northing < spatial_extent["top"]), drop=True)

    # clip data to glacier outline (shapefile)
    points = gpd.points_from_xy(x=subset.easting, y=subset.northing)  # create geometry from ICESat-2 points
    inlier_mask = points.within(glacier_outline.iloc[0].geometry)  # points within shapefile
    subset = subset.where(xr.DataArray(inlier_mask, coords=subset.coords), drop=True) # subset xarray dataset

    # save file
    output_path.parent.mkdir(exist_ok = True)
    subset.to_netcdf(output_path)

    return output_path


# -------------------------------------------------------------------------
# -------------------------------------------------------------------------
# READING ICESAT-2 DATA
# functions from Desiree adapted to xarray outputs
# https://github.com/desireetreichler/snowdepth/blob/main/tools/IC2tools.py
# -------------------------------------------------------------------------
# -------------------------------------------------------------------------

def ATL06_to_dict(filename, dataset_dict):
    """
        Read selected datasets from an ATL06 file
        Input arguments:
            filename: ATl06 file to read
            dataset_dict: A dictinary describing the fields to be read
                    keys give the group names to be read,
                    entries are lists of datasets within the groups
        Output argument:
            D6: dictionary containing ATL06 data.  Each dataset in
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
                if '/gt%d%s/land_ice_segments' % (pair, beam) not in h5f:
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
                                    if dataset in ['h_li_20m']:
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
                    temp['pair'] = np.zeros_like(temp['h_li']) + pair
                    temp['beam'] = np.zeros_like(temp['h_li']) + beam_ind
                    # RGT and cycle are also convenient. They are in the filename.
                    fs = filename.split('_')
                    temp['RGT'] = np.zeros_like(temp['h_li']) + int(fs[-3][0:4])
                    temp['cycle'] = np.zeros_like(temp['h_li']) + int(fs[-3][4:6])
                    # date
                    temp['date'] = np.zeros_like(temp['h_li']).astype(str)  # as type str so that can be replaced with datetime string
                    temp['date'][temp['date'] == '0.0'] = datetime.strptime(np.array(h5f['ancillary_data/data_start_utc'])[0].decode('UTF-8'), '%Y-%m-%dT%H:%M:%S.%fZ')

                    D6.append(temp)
    return D6

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

                    # append date
                    # conversion datetime -> string -> int in order to have int in format YYYYMMDDHHMMSS.
                    temp['date'] = np.zeros_like(temp['h_te_best_fit'])
                    date_datetime = datetime.strptime(np.array(h5f['ancillary_data/data_start_utc'])[0].decode('UTF-8'), '%Y-%m-%dT%H:%M:%S.%fZ')
                    date_str = date_datetime.strftime('%Y%m%d%H%M%S')
                    date_int = int(date_str)
                    temp['date'][temp['date'] == 0] = date_int

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
    # pd_final = gpd.GeoDataFrame(df_final, geometry='geometry', crs='epsg:32633')  # changed from +init-version to avoid the upcoming warning

    pd_final = gpd.GeoDataFrame(df_final)  # geometry will be handled differently because to_netcdf() cannot pass crs

    return pd_final


def ATL06_to_gdf(dataset_path, dataset_dict):
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

    if ('latitude' in dataset_dict['land_ice_segments']) != True:
        dataset_dict['land_ice_segments'].append('latitude')
    if ('longitude' in dataset_dict['land_ice_segments']) != True:
        dataset_dict['land_ice_segments'].append('longitude')


    data_dict = ATL06_to_dict(dataset_path, dataset_dict)
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
    # pd_final = gpd.GeoDataFrame(df_final, geometry='geometry', crs='epsg:32633')  # changed from +init-version to avoid the upcoming warning

    pd_final = gpd.GeoDataFrame(df_final)  # geometry will be handled differently because to_netcdf() cannot pass crs

    return pd_final

def concat_xr(gdf_list, dataproduct):
    """
    adapted from Desiree

    concatanate geodataframes into 1 geodataframe and then convert to xarray dataset
    Inputs : list of geodataframes
    Output : xarray dataset containing everything includint converted coordinated from wgs84 to utm
    """
    # concatenate geodataframes into one
    gdf = pd.concat([gdf for gdf in gdf_list]).pipe(gpd.GeoDataFrame)

    # convert geodataframe to xarray dataset
    ds = gdf.to_xarray()

    # convert latitude and longitude to easting and northing, assign those as variables
    myproj = Proj("+proj=utm +zone=33 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")  # assign projection
    easting, northing = myproj(ds['longitude'], ds['latitude'])
    ds['easting'] = ('index', easting)
    ds['northing'] = ('index', northing)

    if dataproduct == 'ATL06':
        ds = ds.rename({'h_li': 'h'})

    if dataproduct == 'ATL08':
        ds = ds.rename({'h_te_best_fit': 'h'})

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
        'land_segments' : ['latitude', 'longitude', 'delta_time_beg'],
        'land_segments/terrain': ['h_te_best_fit'],
    }

    gdf_list = []
    for file in os.listdir(input_path):
        ds = ATL08_to_gdf(f'{input_path}/{file}', datadict)
        gdf_list.append(ds)

    concat_xr(gdf_list, 'ATL08')

    return output_path


def ATL06_to_xr(input_path, output_path):
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

    # dictionary of variables we want in out final xarray dataset according to the ATL06 product dictionary
    # https://icesat-2-scf.gsfc.nasa.gov/sites/default/files/asas/asasv60/atl08_template.html

    datadict = {
        'land_ice_segments': ['latitude', 'longitude', 'delta_time_beg', 'h_li'],
    }

    gdf_list = []
    for file in os.listdir(input_path):
        ds = ATL06_to_gdf(f'{input_path}/{file}', datadict)
        gdf_list.append(ds)

    concat_xr(gdf_list, 'ATL06')

    return output_path

def read_icesat(dataproduct, output_filepath):
    # work on it later when i can load atl06 and 03 data as well
    # will just point to function according to data product

    if output_filepath.is_file():
        return output_filepath

    if dataproduct == 'ATL08':
        ATL08_to_xr('cache/is2_ATL08', output_filepath)

    if dataproduct == 'ATL06':
        ATL06_to_xr('cache/is2_ATL06', output_filepath)







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

def read_icepyx(input_path, data_product, output_path):

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







