import geopandas as gpd
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
from pathlib import Path

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

    print('subsetting icesat')

    # if subset already exists return path
    if output_path.is_file():
        return output_path

    # load data
    data = xr.open_dataset(input_path, decode_coords=False)

    if input_path == Path('nordenskiold_land-is2.nc'):
        data['h'] = data['h_te_best_fit']

    #    from matplotlib import pyplot as plt
    #    plt.scatter(data.easting, data.northing)
    #    plt.plot([spatial_extent['left'], spatial_extent['right'], spatial_extent['right'], spatial_extent['left']],
    #             [spatial_extent['bottom'], spatial_extent['bottom'], spatial_extent['top'], spatial_extent['top']])
    #    plt.show()

    # clip data to bounding box
    subset = data.where(
        (data.easting > spatial_extent["left"]) & (data.easting < spatial_extent["right"]) & (data.northing > spatial_extent["bottom"]) & (
                    data.northing < spatial_extent["top"]), drop=True)

    print('subset to bbox, now clipping to glacier extent')

    # if subset is empty all the analysis, plotting and validation will be set to False in main.py
    #if subset.isnull() == True:
    #    return 'empty'

    # clip data to glacier outline (shapefile)
    points = gpd.points_from_xy(x=subset.easting, y=subset.northing)  # create geometry from ICESat-2 points
    inlier_mask = points.within(glacier_outline.iloc[0].geometry)  # points within shapefile
    subset = subset.where(xr.DataArray(inlier_mask, coords=subset.coords), drop=True) # subset xarray dataset

    #if subset.isnull():
    #    return 'empty'

    # save date in int format as variable
    subset['date_str'] = ('index', subset.date.values.astype(str))
    subset['date_int'] = ('index', [int(x[:10].replace('-', '')) for x in subset.date_str.values])
    subset['year_int'] = ('index', [int(x[:4]) for x in subset.date_str.values])

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

# common functions
def point_convert(row):
    geom = Point(row['longitude'], row['latitude'])
    return geom

def concat_xr(gdf_list, dataproduct):
    """
    adapted from Desiree

    concatanate geodataframes into 1 geodataframe and then convert to xarray dataset
    Inputs : list of geodataframes
    Output : xarray dataset containing everything includint converted coordinated from wgs84 to utm
    """

    # delete empty geodataframe
    for i in range(len(gdf_list)):
        if gdf_list[i].empty:
            gdf_list.pop(i)

    # concatenate geodataframes into one
    gdf = pd.concat([gdf for gdf in gdf_list]).pipe(gpd.GeoDataFrame)

    # convert geodataframe to xarray dataset
    ds = gdf.to_xarray()

    if dataproduct == 'ATL06':
        ds = ds.rename({'h_li': 'h'})

    if dataproduct == 'ATL08':
        ds = ds.rename({'h_te_best_fit': 'h'})

    if dataproduct == 'ATL03':
        ds = ds.rename({'lon_ph': 'longitude', 'lat_ph': 'latitude', 'h_ph': 'h'})

    # convert latitude and longitude to easting and northing, assign those as variables
    myproj = Proj("+proj=utm +zone=33 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")  # assign projection
    easting, northing = myproj(ds['longitude'], ds['latitude'])
    ds['easting'] = ('index', easting)
    ds['northing'] = ('index', northing)

    ds.to_netcdf(f'data/icesat_{dataproduct}.nc')

def read_icesat(dataproduct, output_filepath):
    """
    A crossroad for which function to call based on ICESat-2 product.
    """

    if output_filepath.is_file():
        return output_filepath

    if dataproduct == 'ATL08':
        ATL08_to_xr('cache/is2_ATL08', output_filepath)

    if dataproduct == 'ATL06':
        ATL06_to_xr('cache/is2_ATL06', output_filepath)

    if dataproduct == 'ATL03':
        ATL03_to_xr('cache/is2_ATL03', output_filepath)

#                               ATL08
# -------------------------------------------------------------------
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
                    temp['pair'] = np.zeros_like(temp['h_te_best_fit']) + pair
                    temp['beam'] = np.zeros_like(temp['h_te_best_fit']) + beam_ind
                    # RGT and cycle are also convenient. They are in the filename.
                    fs = filename.split('_')
                    temp['RGT'] = np.zeros_like(temp['h_te_best_fit']) + int(fs[-3][0:4])
                    temp['cycle'] = np.zeros_like(temp['h_te_best_fit']) + int(fs[-3][4:6])

                    # append date
                    # todo: convert date to int as well in the format yyyymmdd (will be helpful later)
                    temp['date'] = np.zeros_like(temp['h_te_best_fit']).astype('datetime64[ns]')
                    temp['date'][temp['date'] != 'abc'] = datetime.strptime(
                        np.array(h5f['ancillary_data/data_start_utc'])[0].decode('UTF-8'), '%Y-%m-%dT%H:%M:%S.%fZ')

                    D6.append(temp)
    return D6

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
        'land_segments' : ['latitude', 'longitude', 'delta_time_beg', 'delta_time', 'dem_h'],
        'land_segments/terrain': ['h_te_best_fit'],
    }

    gdf_list = []
    for file in os.listdir(input_path):
        ds = ATL08_to_gdf(f'{input_path}/{file}', datadict)
        gdf_list.append(ds)

    concat_xr(gdf_list, 'ATL08')

    return output_path

#                               ATL06
# --------------------------------------------------------------------------

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
                    # beam and pair
                    temp['beam'] = np.zeros_like(temp['h_li']) + beam_ind
                    temp['pair'] = np.zeros_like(temp['h_li']) + pair

                    # RGT and cycle are also convenient. They are in the filename.
                    fs = filename.split('_')
                    temp['RGT'] = np.zeros_like(temp['h_li']) + int(fs[-3][0:4])
                    temp['cycle'] = np.zeros_like(temp['h_li']) + int(fs[-3][4:6])
                    # date
                    temp['date'] = np.zeros_like(temp['h_li']).astype('datetime64[ns]')
                    temp['date'][temp['date'] != 'abc'] = datetime.strptime(
                        np.array(h5f['ancillary_data/data_start_utc'])[0].decode('UTF-8'), '%Y-%m-%dT%H:%M:%S.%fZ')
                    D6.append(temp)
    return D6

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
        'land_ice_segments': ['latitude', 'longitude', 'delta_time_beg', 'h_li', 'delta_time', 'dem_h'],
    }

    gdf_list = []
    for file in os.listdir(input_path):
        ds = ATL06_to_gdf(f'{input_path}/{file}', datadict)
        gdf_list.append(ds)

    concat_xr(gdf_list, 'ATL06')

    return output_path

#                               ATL03
# ----------------------------------------------------------------
# adapted for ATL03 by Desiree


def ATL03_to_dict(filename, dataset_dict=False, utmzone=False):
    """
        Read selected datasets from an ATL03 file
        Input arguments:
            filename: ATl03 file to read
            dataset_dict: A dictinary describing the fields to be read
                    keys give the group names to be read,
                    entries are lists of datasets within the groups. If not set,
                    a standard minimum dict of lat, lon, height, time, quality flag is read
            utmzone: optional, if set, lat/lon are converted to the provided utmzone string (e.g.: 33N)
        Output argument:
            D3: dictionary containing ATL03 data.  Each dataset in
                dataset_dict has its own entry in D3.  Each dataset
                in D3 contains a list of numpy arrays containing the
                data
    """
    # filename = ATL03_file[filenr]
    # h5f=h5py.File(filename,'r')
    if dataset_dict == False:
        dataset_dict = {'heights': ['delta_time', 'lon_ph', 'lat_ph', 'h_ph', 'signal_conf_ph']}

    D3 = []
    pairs = [1, 2, 3]
    beams = ['l', 'r']
    # open the HDF5 file
    with h5py.File(filename, 'r') as h5f:  # added mode to 'r', to suppress depreciation warning
        # loop over beam pairs
        for pair in pairs:
            # loop over beams
            for beam_ind, beam in enumerate(beams):
                # check if a beam exists, if not, skip it
                if '/gt%d%s/heights' % (pair, beam) not in h5f:
                    continue
                # print('/gt%d%s/' % (pair, beam))
                # loop over the groups in the dataset dictionary
                temp = {}
                for group in dataset_dict.keys():
                    if group in [
                        'geolocation']:  # check whether this data is available for each photon or for each 20m segment only.
                        segmentlevel = 1
                    elif group in ['heights']:
                        segmentlevel = 0
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
                            # a few attributes have 5 columns, corresponding to land, ocean, sea ice, land ice, inland water
                            try:
                                if len(temp[dataset][0] == 5):
                                    for surftypenr, surftype in enumerate(
                                            ['ocean', 'seaice', 'landice', 'inlandwater']):
                                        temp[dataset + '_' + surftype] = temp[dataset][:, surftypenr + 1]
                                    temp[dataset] = temp[dataset][:, 0]  # default = land, first column
                            except TypeError:  # as e: # added this exception, as I got some type errors - temp[dataset] was 0.0
                                pass
                                # some data is only available at the 20 m segment rate (or even less). Fix this by duplicating
                            if segmentlevel == 1:
                                DS = '/gt%d%s/%s/%s' % (pair, beam, 'geolocation', 'segment_ph_cnt')
                                segment_ph_cnt = np.array(h5f[DS])
                                # pdb.set_trace(); # for tracks with little/no actual data, 'segment_ph_cnt' values seem to sometimes be really high (500 times higher than normal), making this duplication fail
                                temp2 = np.concatenate([np.repeat(y, x) for x, y in zip(segment_ph_cnt, temp[dataset])])
                                temp[dataset] = temp2  # overwrite
                        except KeyError:  # as e:
                            pass
                if len(temp) > 0:
                    # it's sometimes convenient to have the beam and the pair as part of the output data structure: This is how we put them there.
                    # a = np.zeros_like(temp['h_te_best_fit'])
                    # print(a)
                    temp['pair'] = np.zeros_like(temp['h_ph']) + pair
                    temp['beam'] = np.zeros_like(temp['h_ph']) + beam_ind
                    # add x_atc, y_atc
                    temp['x_atc'], temp['y_atc'] = get_ATL03_x_atc(h5f, pair, beam, temp)
                    # add datetime
                    temp['date'] = np.zeros_like(temp['h_ph']).astype('datetime64[ns]')
                    temp['date'][temp['date'] != 'abc'] = datetime.strptime(
                        np.array(h5f['ancillary_data/data_start_utc'])[0].decode('UTF-8'), '%Y-%m-%dT%H:%M:%S.%fZ')

                    if utmzone:  # default: false
                        # add utm XXX x/y
                        temp['utmx'], temp['utmy'] = ATL03_to_utm(temp, utmzone)
                    # print(temp)
                    # temp['filename']=filename
                    D3.append(temp)
    return D3


def ATL03_to_utm(temp, utmzone):
    if utmzone[-1] == 'N':
        northsouth = 'north'
    else:
        northsouth = 'south'
    # utmx=np.zeros_like(temp['h_ph'])+np.NaN
    # utmy=np.zeros_like(temp['h_ph'])+np.NaN
    # convert to x/y utm coordinates
    myProj = Proj("+proj=utm +zone=%s, +%s +ellps=WGS84 +datum=WGS84 +units=m +no_defs" % (
    utmzone, northsouth))  ## assumes we only have one datum (WGMS84, otherwise use transform) and want UTMXXX
    utmx, utmy = myProj(temp['lon_ph'], temp['lat_ph'])  # to convert back, add argument: , inverse=True

    return utmx, utmy


def get_ATL03_x_atc(h5f, pair, beam, temp):
    # calculate the along-track and across-track coordinates for ATL03 photons
    # -- data and attributes for beam gtx
    x_atc = np.zeros_like(temp['h_ph']) + np.NaN
    y_atc = np.zeros_like(temp['h_ph']) + np.NaN
    # -- ATL03 Segment ID
    DS = '/gt%d%s/%s/%s' % (pair, beam, 'geolocation', 'segment_id')
    # Segment_ID = np.array(h5f[DS])
    # Segment_ID[gtx] = val['geolocation']['segment_id']
    # n_seg = len(Segment_ID)#[gtx])
    # -- first photon in the segment (convert to 0-based indexing)
    DS = '/gt%d%s/%s/%s' % (pair, beam, 'geolocation', 'ph_index_beg')
    Segment_Index_begin = np.array(h5f[DS]) - 1
    # Segment_Index_begin[gtx] = val['geolocation']['ph_index_beg'] - 1
    # -- number of photon events in the segment
    DS = '/gt%d%s/%s/%s' % (pair, beam, 'geolocation', 'segment_ph_cnt')
    Segment_PE_count = np.array(h5f[DS])
    # Segment_PE_count[gtx] = val['geolocation']['segment_ph_cnt']
    # -- along-track distance for each ATL03 segment
    DS = '/gt%d%s/%s/%s' % (pair, beam, 'geolocation', 'segment_dist_x')
    Segment_Distance = np.array(h5f[DS])
    # Segment_Distance[gtx] = val['geolocation']['segment_dist_x']
    # -- along-track length for each ATL03 segment
    DS = '/gt%d%s/%s/%s' % (pair, beam, 'geolocation', 'segment_length')
    # Segment_Length = np.array(h5f[DS])
    # Segment_Length[gtx] = val['geolocation']['segment_length']
    # -- Transmit time of the reference photon
    DS = '/gt%d%s/%s/%s' % (pair, beam, 'geolocation', 'delta_time')
    # delta_time = np.array(h5f[DS])
    # delta_time = val['geolocation']['delta_time']
    # -- distance between photons
    DS = '/gt%d%s/%s/%s' % (pair, beam, 'heights', 'dist_ph_along')
    dist_ph_along = np.array(h5f[DS])
    DS = '/gt%d%s/%s/%s' % (pair, beam, 'heights', 'dist_ph_across')
    dist_ph_across = np.array(h5f[DS])
    # -- iterate over ATL03 segments to calculate 40m means
    # -- in ATL03 1-based indexing: invalid == 0
    # -- here in 0-based indexing: invalid == -1
    segment_indices, = np.nonzero((Segment_Index_begin[:-1] >= 0) &
                                  (Segment_Index_begin[1:] >= 0))
    for j in segment_indices:
        # -- index for segment j
        idx = Segment_Index_begin[j]
        # -- number of photons in segment (use 2 ATL03 segments)
        c1 = np.copy(Segment_PE_count[j])
        c2 = np.copy(Segment_PE_count[j + 1])
        cnt = c1 + c2
        # -- time of each Photon event (PE)
        # segment_delta_times = temp['delta_time'][idx:idx+cnt]
        # -- Photon event lat/lon and elevation (WGS84)
        # segment_heights = temp['h_ph'][idx:idx+cnt]
        # segment_lats = temp['lat_ph'][idx:idx+cnt]
        # segment_lons = temp['lon_ph'][idx:idx+cnt]
        # -- Along-track and Across-track distances
        distance_along_X = np.copy(dist_ph_along[idx:idx + cnt])
        distance_along_X[:c1] += Segment_Distance[j]
        distance_along_X[c1:] += Segment_Distance[j + 1]
        distance_along_Y = np.copy(dist_ph_across[idx:idx + cnt])
        x_atc[idx:idx + cnt] = distance_along_X
        y_atc[idx:idx + cnt] = distance_along_Y

    return x_atc, y_atc


def ATL03_to_gdf(ATL03_fn, dataset_dict=False, aoicoords=False, filterbackground=False, utmzone=False, v=False):
    """
    function to convert ATL03 hdf5 to geopandas dataframe, containing columns as passed in dataset dict. Based on Ben's functions.

    additionally: aoicoords -> [xmin,ymin,xmax,ymax] if set, the data will be clipped to that bounding box.
                  filterbackground -> default False, otherwise set to remove values (e.g. [-2, -1,0, 1], only excluded if true for BOTH land (standard) signal_conf_ph and the one for land ice)
                  v: if set to True, the function prints the current file - keeping track of progress in a loop.

                  signal_conf_ph meaning/values available: Confidence level associated with each photon event selected as signal.
                  0=noise. 1=added to allow for buffer but algorithm classifies as background; 2=low; 3=med; 4=high). This parameter
                  is a 5xN array where N is the number of photons in the granule, and the 5 rows indicate signal finding for each
                  surface type (in order: land, ocean, sea ice, land ice and inland water). Events not associated with a specific surface
                  type have a confidence level of ­1. Events evaluated as TEP returns have a confidence level of ­2. flag_values: ­2, ­1, 0, 1, 2, 3, 4
                  flag_meanings : possible_tep not_considered noise buffer low medium high
    """
    if dataset_dict == False:
        dataset_dict = {'heights': ['delta_time', 'lon_ph', 'lat_ph', 'h_ph', 'signal_conf_ph'],
                        'geophys_corr' : ['dem_h']}
    clip = False
    if type(aoicoords) != type(False):  # aoicoords.any():
        xmin, ymin, xmax, ymax = aoicoords
        clip = True

    if ('lat_ph' in dataset_dict['heights']) != True:
        dataset_dict['heights'].append('lat_ph')
    if ('lon_ph' in dataset_dict['heights']) != True:
        dataset_dict['heights'].append('lon_ph')
    # use the above function to convert to dict

    # verbose: keep track of current file
    if v: print('converting ' + ATL03_fn + ' to gdf...')

    data_dict = ATL03_to_dict(ATL03_fn, dataset_dict, utmzone)
    if len(data_dict) > 0:  # added this to account for empty data_dicts, which occured
        # this will give us 6 tracks
        i = 0
        for track in data_dict:
            # 1 track
            # check that all data have the same length - sometimes, the multiplication with segment_ph_cnt fails. Set these to Nan.
            nrdatapts = len(track['delta_time'])
            for key in track.keys():
                if len(track[key]) != nrdatapts:
                    track[key] = np.empty_like(track['delta_time']) * np.nan
                    if v:
                        print(f'dropped {key}: wrong nr of data points')
            # convert to datafrmae
            df = pd.DataFrame(track)
            # filter by aoi (owerwrite df)
            if clip:
                df = df.loc[
                    (df['lon_ph'] > xmin) & (df['lon_ph'] < xmax) & (df['lat_ph'] > ymin) & (df['lat_ph'] < ymax)]
            # filter photons classified as background (0,1, for land / ice), owerwrite df - should this also include filtering not assigned (-1)? TBD
            if filterbackground:
                df = df[(~df['signal_conf_ph'].isin(filterbackground)) | (
                    ~df['signal_conf_ph_landice'].isin(filterbackground))]
                # old filter method, discarded
                # df = df.loc[((df['signal_conf_ph'] >1 ) | (df['signal_conf_ph'] == -1 )) &  ((df['signal_conf_ph_landice'] >1)| (df['signal_conf_ph_landice'] == -1 ))]
            # add track/beam
            try:
                df['pb'] = df['pair'] * 10 + df['beam']
                # df['p_b'] = str(track['pair'][0])+'_'+str(track['beam'][0])
            except:  # added, to account for errors - maybe where there is onluy one data point (?)
                df['pb'] = track['pair'] * 10 + track['beam']
                # df['p_b'] = str(track['pair'])+'_'+str(track['beam'])

            if i == 0:
                df_final = df.copy()
            else:
                df_final = pd.concat([df,
                                      df_final])  # possible solution? Not quite yet it seems - FutureWarning: The frame.append method is deprecated and will be removed from pandas in a future version. Use pandas.concat instead.
                # df_final = df_final.append(df)
            i = i + 1
        try:
            gdf_final = gpd.GeoDataFrame(df_final, geometry=gpd.points_from_xy(x=df_final.lon_ph, y=df_final.lat_ph),
                                         crs='epsg:32633')  # changed from +init-version to avoid the upcoming warning
            gdf_final = gdf_final.drop(columns='geometry')  # very not nice fix but 1) do not need geometry columns, 2) didn work to just comment this part out, 3) xarray doesnt know how to convert geometry type to netcdf so... byebye geometry
        except:  # added this exception, as I got some errors that the df_final was not defined when there was a problem reading out height data for the granule - skip
            gdf_final = gpd.GeoDataFrame()  # empty frame
    else:
        gdf_final = gpd.GeoDataFrame()  # empty frame

    return gdf_final


def ATL03_to_xr(input_path, output_path):
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

    datadict = {'heights': ['delta_time', 'lon_ph', 'lat_ph', 'h_ph', 'signal_conf_ph']}

    gdf_list = []
    for file in os.listdir(input_path):
        ds = ATL03_to_gdf(f'{input_path}/{file}', datadict)
        gdf_list.append(ds)

    concat_xr(gdf_list, 'ATL03')

    return output_path


def groupby_hydroyear(data, year, splitday):
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
    hydrosilvestr = year * 10000 + splitday
    subset = data.where((data.date_int.values > hydrosilvestr) & (data.date_int.values <= hydrosilvestr + 10000))
    subset = subset.dropna('index')

    return subset
