from shapely.geometry import Point
import geopandas as gpd
from pyproj import Proj
import rasterio as rio
import numpy as np
from sklearn import linear_model
from shapely.ops import unary_union
import pandas as pd
from pathlib import Path
from user_vars import label


def latlon2UTM(df):
    """
    Convert latitude and longitude to easting and northing.
    :param df: input df with 'lat', 'lon'
    :return: new df with columns 'easting', 'northing'
    """

    # set projection parameters
    myproj = Proj("+proj=utm +zone=33 +north +ellps=WGS84 +datum=WGS84 +units=m +no_defs")

    # convert
    easting, northing = myproj(df['longitude'], df['latitude'])

    # add columns to df
    df['easting'] = easting
    df['northing'] = northing

    return df


def xy2geom(df, x_column, y_column, geom_column):
    """
    Makes new geometry column from easting and northing and converts df to gdf in crs UTM zone 33.

    :param df: input dataframe (ICESat-2 data with columns easting and northing)

    :return: geodataframe in EPSG:32633
    """

    # create geometry from easting, northing
    df[geom_column] = [Point(xy) for xy in zip(df[x_column], df[y_column])]

    # convert df to df
    gdf = gpd.GeoDataFrame(df, geometry=geom_column).set_crs('EPSG:32633')

    return gdf


def dh(data):
    # path to DEM mosaic vrt in SvalbardSurges (had to copy folder cache/NP_DEMs to current folder for this to work)
    dem_path = 'C:/Users/eliss/Documents/SvalbardSurges/cache/npi_mosaic.vrt'

    outpath = Path(f'data/{label}_dh.csv')

    if outpath.is_file():
        data = pd.read_csv(outpath, engine="pyarrow")
        return data

    with rio.open(dem_path) as raster:
        print('doing icesat-dem')
        data["dem_elevation"] = list(np.fromiter(
            raster.sample(
                np.transpose([data.easting.values, data.northing.values]),
                masked=True
            ),
            dtype=raster.dtypes[0],
            count=data.easting.shape[0]
        ))

    # subtract ICESat-2 elevation from DEM elevation (with elevation correction)
    data["dh"] = data["h"] - data["dem_elevation"] - 29.55
    data["dh_uncorr"] = data["h"] - data["dem_elevation"]

    # todo a bit better correction

    # get rid of nan values in ATL06
    data = data[data['h'] < 1800]
    data = data.dropna(subset=['dh'])

    print('saving dh file')
    data.to_csv(outpath)

    return data


def groupByHydroYear(data, year, glacier_id):
    """
    Groups data by given hydrological year. Saves the data as .csv to temp folder.
    """

    year = int(year)
    output_path = Path(f'temp/glaciers/{glacier_id}_{year}.gpkg')

    # cache
    if output_path.is_file():
        return

    try:
        print(data['acquisition_time'])
    except:
        data['acquisition_time'] = data['date']

    data['date'] = [str(x) for x in data['acquisition_time']]

    data = data.dropna(subset=['dh'])
    data = data.dropna(subset=['acquisition_time'])

    # split data into day, month, year
    data['day'] = [int(x[8:10]) for x in data['date']]
    data['month'] = [int(x[5:7]) for x in data['date']]
    data['year'] = [int(x[0:4]) for x in data['date']]

    # select data that belong in hydrological year
    subset = data[((data['year'] == year - 1) & (data['month'] > 10)) |
                  ((data['year'] == year) & (data['month'] < 11))]

    # save as csv and gpkg
    #subset['geometry'] = subset['geometry'].apply(wkt.loads)
    #gdf = gpd.GeoDataFrame(subset, geometry='geometry', crs='EPSG:32633')
    subset.to_file(output_path)

    return


def normalize(data):
    """
    Normalize h and dh in ICESat-2 data.

    params
    ------
    - inpath
        input path (Path object)
    - outpath
        output path (Path object)

    returns
    -------
    output path
    """

    # remove lowest 3% of dataset
    data = data[data['dem_elevation'] > ((max(data['dem_elevation']) - min(data['dem_elevation'])) * 0.03)]

    # normalize dem_elevation
    min_h = min(data.dem_elevation.values)
    max_h = max(data.dem_elevation.values)
    data['h_norm'] = (data['dem_elevation'] - min_h) / (max_h - min_h)

    return data


def clipICESat(data, glacier):
    """
    Function with same structure as clip() but not working with GeoDataFrame as input.
    """

    glacier_id = list(glacier['glims_id'].values)[0]

    # clip data to bounding box
    bbox = glacier.geometry.iloc[0].bounds
    subset = data.where(
        (data.easting > bbox[0]) & (data.easting < bbox[2]) & (
                    data.northing > bbox[1]) & (
                data.northing < bbox[3])).dropna(subset = ['easting'])

    # clip to shapefile outline
    # convert subset to gdf
    subset['geometry'] = gpd.points_from_xy(x=subset.easting, y=subset.northing)
    subset = gpd.GeoDataFrame(subset, geometry='geometry')
    subset = subset.set_crs(32633)
    clipped = gpd.clip(subset, glacier)

    #points = gpd.points_from_xy(x=subset.easting, y=subset.northing)  # create geometry from ICESat-2 points
    #inlier_mask = points.within(glacier.iloc[0].geometry)  # points within shapefile
    #clipped = subset.where(pd.DataArray(inlier_mask))

    return clipped


def filterData(data, glacier_id, glacier_name, skipcache=None):

    outpath = Path(f'data/temp/glaciers/{glacier_id}_filtered.gpkg')

    if skipcache == None:
        if outpath.is_file():
            return

    # get rid of values larger than highest point on DEM (with elevation correction)
    data = data[data['h'] < data.dem_elevation+80]
    data = data[data['h'] > data.dem_elevation-80]

    # plot to see
    import matplotlib.pyplot as plt
    plt.scatter(data.h, data.dh)
    plt.title(f'ATL06: filter by h')
    plt.savefig(f'data/temp/figs/{glacier_id}_{glacier_name}_filtered.png')
    plt.close()

    # cache files
    data.to_file(outpath)

    return data


def filterWithATL08(data, glacier_id, skipcache=None):

    outpath = Path(f'data/temp/glaciers/{glacier_id}_filtered_ATL08.gpkg')

    if skipcache == None:
        if outpath.is_file():
            return

    print('xytogeom')
    # create new geometry (h, dh) so that i can make buffer etc.
    data = xy2geom(data, 'h', 'dh', 'computing_geom')

    # split the data into reference data and filter data
    ref_data = data[data['product'] != 'ATL06']
    ref_data = gpd.GeoDataFrame(ref_data, geometry='computing_geom')
    filter_data = data[data['product'] == 'ATL06']
    filter_data = gpd.GeoDataFrame(filter_data, geometry='computing_geom')

    print('create buffers')
    # create buffer around the reference data
    buffers = ref_data.buffer(20)
    buff = gpd.GeoSeries(unary_union(buffers))

    print('masking')
    # loop through points and create mask list of True/False (in/out)
    mask = []
    for i, row in filter_data.iterrows():
        if row['computing_geom'].intersects(buff)[0]:
            mask.append(True)
        else:
            mask.append(False)

    # filter data based on mask
    filter_data['mask'] = mask
    filtered_data = filter_data[filter_data['mask'] == True]

    print('merging')
    # merge the datasets
    merge_result = pd.concat([ref_data, filtered_data])

    import matplotlib.pyplot as plt
    plt.scatter(merge_result.h, merge_result.dh)
    plt.title(f'ATL06: filtering by ATL08')
    plt.savefig(f'data/temp/figs/{glacier_id}_filtered_atl08.png')
    plt.close()

    print('to geodataframe')
    # fix geometries
    outdata = merge_result.drop(columns=['mask', 'computing_geom'])
    outdata = gpd.GeoDataFrame(outdata, geometry='geometry', crs=32633)

    print('normalizing')
    # normalize before saving
    import analysis
    outdata = analysis.normalize(outdata)

    print('exporting')
    # save
    outdata.to_file(outpath, geometry='geometry')

    return outdata


def filterWithRANSAC(data, glacier_id, skipcache=None):

    # reshape arrays
    X = data.dem_elevation.values.reshape(-1, 1)
    y = data.h.values.reshape(-1, 1)

    # Robustly fit data with ransac algorithm
    ransac = linear_model.RANSACRegressor(max_trials=100)
    ransac.fit(X, y)

    inlier_mask = ransac.inlier_mask_
    outlier_mask = np.logical_not(inlier_mask)

    # Predict data of estimated models (draw the line)
    line_X = np.arange(X.min(), X.max())[:, np.newaxis]

    # ransac coefficient
    coef = ransac.estimator_.coef_[0][0]

    # get rid of outlier data
    data['mask'] = inlier_mask
    data = data[data['mask'] == True]

    data.drop(columns=['mask'])
    data = gpd.GeoDataFrame(data, geometry='geometry', crs=32633)

    return data


def mergeProducts(products):
    """
    Merges the input products into one and saved as .nc. Based on product names automatically
    finds the saved files.

    :param products: list of product names (f.ex.: ['ATL06', 'ATL08'])

    :return: merged xarray dataset
    """

    # initialize empty dataframe
    merged = pd.DataFrame()

    dir = Path('data/')
    for product in products:
        data = pd.read_csv(dir / f'{product}.csv', engine="pyarrow")
        merged = pd.concat([merged, data])

    merged.to_csv('data/ICESat.csv')

    return merged

def pointsToGeoDataFrame(data):
    """
    Converts DataFrame to GeoDataFrame. Is not reccommended to be used on huge datasets because it takes ages.

    :param data: Input DataFrame.

    :return: Saves GDF as file and returns GeoDataFrame of input DataFrame.
    """

    outpath = Path(f'data/temp/{label}_icesat.shp')

    # cache
    if outpath.is_file():
        return gpd.read_file(outpath)

    # convert DF to GDF and save
    gdf = xy2geom(data, 'easting', 'northing', 'geometry')
    try:
        gdf.to_file(outpath)
    except:
        print('unable to save gdf')

    return gdf


def whatIsWrongWithATL06():
    import matplotlib.pyplot as plt
    import geopandas as gpd
    import pandas as pd
    import os

    os.chdir('C:/Users/eliss/Documents/diplomka')

    atl06 = pd.read_csv('data/data/ATL06.csv', engine="pyarrow")
    atl08 = pd.read_csv('data/data/ATL08.csv', engine="pyarrow")

    latitudes = []
    longitudes = []
    eastings = []
    northings = []
    h08 = []
    h06 = []
    dh08 = []
    dh06 = []
    differences = []

    # find same points
    for i in range(len(atl06)):
        lat = atl06['latitude'].iloc[i]
        lon = atl06['longitude'].iloc[i]
        if (lat in list(atl08['latitude'].values)) & (lon in list(atl08['longitude'].values)) & ((atl06['dh'].iloc[i] < -200) | (atl06['dh'].iloc[i] > -200)):

            # todo if years are not the same

            atl08pt = atl08.where((atl08.latitude == lat) & (atl08.longitude == lon)).dropna()
            difference = atl06['h'].iloc[i] - list(atl08pt['h'].values)[0]

            print(difference)

            latitudes.append(lat)
            longitudes.append(lon)
            eastings.append(atl06.easting.iloc[i])
            northings.append(atl06.northing.iloc[i])
            h06.append(atl06.h.iloc[i])
            dh06.append(atl06.dh.iloc[i])
            differences.append(difference)
            h08.append(list(atl08pt['h'].values)[0])
            dh08.append(list(atl08pt['dh'].values)[0])

        else:
            print('not in both datasets')

    diffs = pd.DataFrame()
    diffs['latitude'] = latitudes
    diffs['longitude'] = longitudes
    diffs['dh08'] = dh08
    diffs['dh06'] = dh06
    diffs['h06'] = h06
    diffs['h08'] = h08
    diffs['easting'] = eastings
    diffs['northing'] = northings
    diffs['difference'] = differences

    diffs.to_csv('data/temp/whatiswrongwithatl06.csv')
    print(diffs.head())




