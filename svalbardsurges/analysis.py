import xarray as xr
import numpy as np
import warnings
import rasterio as rio
from matplotlib import pyplot as plt
from sklearn import linear_model
from sklearn.cluster import KMeans, DBSCAN, SpectralClustering
from sklearn.mixture import GaussianMixture
import pandas as pd
from scipy.optimize import curve_fit
from shapely.geometry import Polygon
import shapely

from svalbardsurges.controllers import pltshow, pltsave

# Catch a deprecation warning that arises from skgstat when importing xDEM
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem

from svalbardsurges.inputs import icesat
from pathlib import Path


def groupByHydroYear(input_path, year, output_path):
    """

    :param input_path:
    :return:
    """

    # cache
    if output_path.is_file():
        return output_path

    # open data
    data = xr.open_dataset(input_path)

    # split data by hydrosilvestr
    hydrosilvestr = year * 10000 + 1031
    subset = data.where(
        (data.date_int.values > hydrosilvestr - 10000) & (data.date_int.values <= hydrosilvestr))
    subset = subset.dropna('index')

    subset.to_netcdf(output_path)

    return output_path


def icesatDEMDifference(icesat_path, dem_path, output_path):
    """
    Get elevation difference between ICESat-2 data and reference DEM.

    Parameters
    ----------
    - dem
        path to reference dem
    - icesat_path
        path to ICESat-2 dataset

    Returns
    -------
    ICESat-2 dataset with the additional values of "dem_elevation" (retained values of reference DEM)
    and "dh" (difference between ICESat-2 and reference DEM)
    """

    # cache
    if output_path.is_file():
        return output_path

    # open data
    data = xr.open_dataset(icesat_path)

    with rio.open(dem_path) as raster, warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='.*converting a masked element to nan.*')
        data["dem_elevation"] = "index", np.fromiter(
            raster.sample(
                np.transpose([data.easting.values, data.northing.values]),
                masked=True
            ),
            dtype=raster.dtypes[0],
            count=data.easting.shape[0]
        )

    plt.close('all')

    # subtract ICESat-2 elevation from DEM elevation (with elevation correction)
    data["dh"] = data["h"] - data["dem_elevation"] - 31.55  # todo a bit better correction

    data = data.dropna('index')
    #if data.dropna('index')['dh'].size == 0:
    #    return 'nodata'

    # save as netcdf file
    data.to_netcdf(output_path)

    return output_path


def create_bins(data_path):
    # open data
    data = xr.open_dataset(data_path)

    bins = np.nanpercentile(data["dem_elevation"], np.linspace(0, 100, 6))
    bins = np.nanpercentile(data['dem_elevation'], np.linspace(0, 100, 4))
    # bin for every 100 meters
    bins = np.array([0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100])

    return bins


def icesatHypso(icesat_data, bins):
    """
    Hypsometric binning of glacier elevation changes.

    Parameters
    ----------
    - input_path
        path to IS2 dataset containing the variables 'dh' and 'dem_elevation'
    - bins

    - results_df
        dataframe for storing 1s and 0s as in surge/no surge

    Returns
    -------
    Pandas dataframe of elevation bins, plot of hypsometric elevation change for each year in dataset.
    """

    # open data
    data = icesat_data

    hypso = xdem.volume.hypsometric_binning(
            ddem=data['dh'],
            ref_dem=data['dem_elevation'],
            kind="custom",
            bins=bins,
            aggregation_function=np.nanmean
    )

    return hypso


def linRegHypso(x, y):
    # remove Nans from list
    x, y = removeNans(x, y)

    # if less than more than 7 bins are empty then nodata
    if len(y) < 3:
        return np.nan, np.nan

    # linear regression on binned data
    x = x.reshape(-1, 1)
    y = y.reshape(-1, 1)

    # fit linear model
    lr = linear_model.LinearRegression()
    lr.fit(x, y)

    line_X = np.arange(x.min(), x.max())[:, np.newaxis]
    line_y = lr.predict(line_X)

    # plot
    #plt.plot(line_X, line_y, color="navy", linewidth=2, label="Linear regressor")

    # coefficient
    slope = lr.coef_[0][0]
    intercept = lr.intercept_[0]

    return slope, intercept


def plotHypso(hypso, glacier_name):
    # todo least squares, figure out other means of identifying outliers (surges)
    # todo leave evaluating, move plotting

    if pltshow:
        # initiate plot
        fig, axs = plt.subplots(2, 2)
        plt.suptitle(f'{glacier_name}')

        # prepare data
        x = hypso.index.mid
        y = hypso.value

        # remove Nans from list
        x, y = removeNans(x, y)

        # now try to put a curve through it
        from scipy.optimize import curve_fit

        # plot data
        plt.scatter(x, y, color='orange', marker='.')  # points
        # linear regression scikit
        x = x.reshape(-1, 1)
        y = y.reshape(-1, 1)

        # fit linear model
        lr = linear_model.LinearRegression()
        lr.fit(x, y)

        line_X = np.arange(x.min(), x.max())[:, np.newaxis]
        line_y = lr.predict(line_X)

        # plot
        plt.plot(line_X, line_y, color="navy", linewidth=2, label="Linear regressor")

        # coefficient
        coef = lr.coef_[0][0]


        fig.supxlabel('elevation bins')
        fig.supylabel('average elevation change')
        plt.tight_layout()

        if pltshow:
            plt.show()

    return


def removeNans(x, y):
    try:
        x = x.tolist()
    except:
        x = x.values.tolist()
    try:
        y = y.tolist()
    except:
        y = y.values.tolist()
    a = x
    b = y
    # todo describe function
    # go through elements of list
    unwanted = []
    for i in range(len(b)):
        # if value is nan, then remove the value from the list (don't plot, doesn't go in the analysis)
        if not b[i] < 10000:  # todo IMPROVE (this is a very quick and ugly fix for getting rid of nans)
            unwanted.append(i)

    # delete the unwanted nans (based on index)
    for i in sorted(unwanted, reverse=True):
        del a[i]
        del b[i]

    # convert back to arrays
    x = np.array(a)
    y = np.array(b)
    return x, y


def Gauss(x, A, B):
    y = A*np.exp(-1*B*x**2)
    return y


def hypso_dem(dems, bins, ref_dem):
    """
    Hypsometric binning of glacier elevation changes from ArcticDEM data. Function used for
    validation.

    Parameters
    ----------
    - dems
        dictionary containing paths leading to yearly DEMs
    - ref_dem
        reference DEM from 2010

    Returns
    -------
    Dictionary of binned data.
    """

    # load reference DEM
    ref_dem = xdem.DEM(ref_dem)

    # create bins
    #bins = np.nanpercentile(ref_dem.data.filled(np.nan), np.linspace(0, 100, 6))
    #bins[-1] *= 1.1

    #bins = np.array([0, 250, 500, 750, 900])

    # initialize empty dictionary for storing binned data
    hypso = {}

    for year in dems:
        # create difference DEM (current year compared to 2010)
        d_dem = xdem.DEM(dems[year]) - ref_dem

        # no empty values
        if np.count_nonzero(np.isfinite(d_dem.data.filled(np.nan))) == 0:
            continue

        # hypsometric binning
        hypso[year] = xdem.volume.hypsometric_binning(ddem=d_dem.data, ref_dem=ref_dem.data, kind='custom', bins=bins)

    return hypso


def ransacAlg(data, glacier_name):
    """

    Params
    ------
    - data
        xarray
    - thresholds
        list containing two values: [low threshold, high threshold]

    """

    # do it only on the whole glacier (not split by bins)
    if data.index.size == 0:
        return np.nan

    year = max(data.year_int.values)

    #plt.suptitle(f'{str(year - 1)[:4]}-{str(year)[:4]}, {glacier_name}, {algorithm}')

    lw = 2  # linewidth for plots

    # reshape arrays
    X = data.h.values.reshape(-1, 1)
    y = data.dh.values.reshape(-1, 1)

    # Robustly fit data with ransac algorithm
    ransac = linear_model.RANSACRegressor(max_trials=100)
    ransac.fit(X, y)

    inlier_mask = ransac.inlier_mask_
    outlier_mask = np.logical_not(inlier_mask)

    # Predict data of estimated models
    line_X = np.arange(X.min(), X.max())[:, np.newaxis]
    line_y_ransac = ransac.predict(line_X)

    # PLOT
    #plt.scatter(X[inlier_mask], y[inlier_mask], color="yellowgreen", marker=".", label="Inliers")
    #plt.scatter(X[outlier_mask], y[outlier_mask], color="gold", marker=".", label="Outliers")
    #plt.plot(line_X, line_y_ransac, color="cornflowerblue", linewidth=lw, label="RANSAC regressor")

    # ransac coefficient
    coef = ransac.estimator_.coef_[0][0]

    #plt.title(f'{str(year - 1)[:4]}-{str(year)[:4]}, {glacier_name}, {algorithm}, {coef}')
    #plt.xlabel("Input")
    #plt.ylabel("Response")

    return X, y, inlier_mask, outlier_mask, line_X, line_y_ransac, coef

def linRegAlg(data, glacier_name):

    if data.index.size == 0:
        return 'nodata'

    # reshape arrays
    X = data.h.values.reshape(-1, 1)
    y = data.dh.values.reshape(-1, 1)

    # Fit line
    lr = linear_model.LinearRegression()
    lr.fit(X, y)

    line_X = np.arange(X.min(), X.max())[:, np.newaxis]
    line_y = lr.predict(line_X)

    # plot
    # plt.scatter(X, y, color="yellowgreen", marker='.')
    # plt.plot(line_X, line_y, color="navy", linewidth=lw, label="Linear regressor")

    # coefficient
    coef = lr.coef_[0][0]
    return X, y, line_X, line_y, coef


def linreg(data):

    if data.index.size == 0:
        return np.nan, np.nan

    # reshape arrays
    X = data.h.values.reshape(-1, 1)
    y = data.dh.values.reshape(-1, 1)

    # Fit line
    lr = linear_model.LinearRegression()
    lr.fit(X, y)

    line_X = np.arange(X.min(), X.max())[:, np.newaxis]
    line_y = lr.predict(line_X)

    coef = lr.coef_[0][0]

    #plt.scatter(X, y, color="orange", marker='.', s=2)
    #plt.plot(line_X, line_y, color="navy", linewidth=2, label="Linear regressor")
    #ax.invert_xaxis()

    return coef


def ransac(data, glacier_name):

    fig, axs = plt.subplots(2, 2)

    coefs = {}

    # group by hydrological years
    years = np.unique(data.year_int.values)
    i=1
    for year in years:
        if (year != years[-1]): # | (year != years[0]):
            subset = icesat.groupby_hydroyear(data, year)
            X, y, inlier_mask, outlier_mask, line_X, line_y_ransac, coef = ransacAlg(subset, glacier_name)

            # plot
            ax = plt.subplot(2, 2, i)
            plt.scatter(X[inlier_mask], y[inlier_mask], color="yellowgreen", marker=".", s=2, label="Inliers")
            plt.scatter(X[outlier_mask], y[outlier_mask], color="orange", marker=".", s=2, label="Inliers")
            plt.plot(line_X, line_y_ransac, color="cornflowerblue", linewidth=2, label="RANSAC regressor")

            ax.invert_xaxis()
            plt.title(f'{year}')

            i=i+1
            # append coefficient to values df
            coefs[year] = coef

    plt.suptitle(f'{glacier_name}')
    fig.supxlabel('elevation')
    fig.supylabel('elevation change since 2010')
    plt.tight_layout()
    if pltshow:
        plt.show()

    return coefs


def updateSurgeSum(df):

    for year in df:
        df[year]['sum'] = df[year]['hypso'] + df[year]['ransac']

    return df


def clusterAnalysis(data, glacier_name,
                    dbscan=True, kmeans=False, gaussianmixture=False, spectralclustering=False):

    """
    i dont think a cluster analysis is the way to go - usually the surge is only a couple of points
    and it is not really "deconnected" from the rest of the data points so the pts are usually
    either considered outliers (not it any cluster) or connected with other pts that are not
    part of the surge
    """

    # subset only lower half of the glacier
    middle = (max(data['h']) + min(data['h']))/2
    data = data.where(data['h'] < middle)

    fig, axs = plt.subplots(2, 2)
    plt.suptitle(f'{glacier_name}: DBSCAN')

    i = 1
    # group by hydrological years
    years = np.unique(data.year_int.values)
    for year in years:
        if (year != years[-1]): # | (year != years[0]):
            if i == 5:
                continue
            subset = icesat.groupby_hydroyear(data, year)
            x = subset['h']
            y = subset['dh']

            # convert to array of vectors
            X = toVectorArray(x, y)

            ax = plt.subplot(2, 2, i)

            if dbscan:
                algDBSCAN(X, 2)  # todo what if there is too many holes in data so it does not identify the surge as a cluster?

            if gaussianmixture:
                algGaussianMixture(X)

            if kmeans:
                algKMeans(X)

            if spectralclustering:
                algSpectralClustering(X)

            plt.title(f'{str(year + 1)[:4]}')
            ax.invert_xaxis()

            i = i + 1

    fig.supxlabel('elevation')
    fig.supylabel('elevation change since 2010')
    plt.tight_layout()
    if pltshow:
        plt.show()

    return


def algKMeans(X):
    # run kMeans
    kmeans = KMeans(n_clusters=2, n_init="auto").fit_predict(X)
    plt.scatter(X[:, 0], X[:, 1], c=kmeans)
    return


def algSpectralClustering(X):
    # not working at all for some reason
    clustering = SpectralClustering(n_clusters=2).fit_predict(X)
    plt.scatter(X[:, 0], X[:, 1], c=clustering)

    return


def algGaussianMixture(X):
    y_pred = GaussianMixture(n_components=3).fit_predict(X)
    plt.scatter(X[:, 0], X[:, 1], c=y_pred)
    return


def gmm_bic_score(estimator, X):
    """Callable to pass to GridSearchCV that will use the BIC score."""
    # Make it negative since GridSearchCV expects a score to maximize
    return -estimator.bic(X)


def algDBSCAN(X, n_clusters):
    # run DBSCAN
    db = DBSCAN(eps=40, min_samples=5).fit(X)
    labels = db.labels_

    # Number of clusters in labels, ignoring noise if present.
    n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
    n_noise_ = list(labels).count(-1)

    print("Estimated number of clusters: %d" % n_clusters_)
    print("Estimated number of noise points: %d" % n_noise_)
    unique_labels = set(labels)
    core_samples_mask = np.zeros_like(labels, dtype=bool)
    core_samples_mask[db.core_sample_indices_] = True

    colors = [plt.cm.Spectral(each) for each in np.linspace(0, 1, len(unique_labels))]
    for k, col in zip(unique_labels, colors):
        if k == -1:
            # Black used for noise.
            col = [0, 0, 0, 1]

        class_member_mask = labels == k

        xy = X[class_member_mask & core_samples_mask]
        plt.plot(
            xy[:, 0],
            xy[:, 1],
            ".",
            c=tuple(col),
            markersize=6,
        )

        xy = X[class_member_mask & ~core_samples_mask]
        plt.plot(
            xy[:, 0],
            xy[:, 1],
            ".",
            c=tuple(col),
            markersize=2,
        )

    plt.title(f"clusters: {n_clusters_}")

    return


def toVectorArray(x, y):
    # initiate empty list
    vectors = []
    # loop through indices
    for i in x.index.values:
        xx = x.loc[i].values.item()
        yy = y.loc[i].values.item()

        vectors.append([xx, yy])

    arr = np.array(vectors)

    return arr


def lsFun(x, a, b):
    y = a*x + b
    return y


# todo spectral clustering BIRCH, others?
# https://scikit-learn.org/stable/auto_examples/cluster/plot_cluster_comparison.html#sphx-glr-auto-examples-cluster-plot-cluster-comparison-py


def classifyRF(df, training_data):
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score, ConfusionMatrixDisplay
    from sklearn.model_selection import RandomizedSearchCV, train_test_split
    from scipy.stats import randint
    from sklearn.tree import export_graphviz
    from IPython.display import Image

    plt.close('all')
    #plt.scatter(df['slope'], df['max_dh'], c=df['year'])
    #plt.show()

    # remove nans from datasets
    df = df.dropna(axis='index')
    training_data = training_data.dropna(axis='index')

    # remove glaciers in training dataset from dataset
    for i in df.index.values:
        # get glacier id of
        glac_id = df._get_value(i, 'glacier_id')
        if glac_id in training_data.glacier_id.values:
            df = df.drop(index=i)

    # Split the data into features (X) and target (y)
    X = df.drop(columns=['surging_rf', 'surging_threshold', 'glacier_id', 'year', 'geom', 'name', 'dh_path', 'intercept', 'bin_max'])
    y = df.surging_rf.replace({True: 1, False: 0})

    # split training dataset into features and target
    X_train = training_data.drop(columns=['surging_rf', 'surging_threshold', 'glacier_id', 'year', 'geom', 'name', 'dh_path', 'intercept', 'bin_max'])
    y_train = training_data.surging_rf.replace({True: 1, False: 0})

    # fitting and evaluating the model
    rf = RandomForestClassifier()
    rf.fit(X_train, y_train)

    # evaluate the model by comparison with actual data
    y_pred = rf.predict(X_train)
    accuracy = accuracy_score(y_train, y_pred)
    print(accuracy)

    X['surging_rf'] = rf.predict(X)
    df = df.drop(columns=['surging_rf'])
    result = pd.concat([df, X], axis=1, join='inner')

    # merge results with training data for plotting
    #result['training'] = 0
    #training_data['training'] = 1
    #result = pd.concat([result, training_data], axis=1, join='inner')

    for year in [2018, 2019, 2020, 2021, 2022, 2023]:
        print(year)
        for index, row in result.iterrows():
            if row['year'] == year:
                polygon = shapely.wkt.loads(row['geom'])
                if row['surging_rf'] == 1:
                    print(row['name'], 1)
                    c = 'orange'
                else:
                    print(row['name'], 0)
                    c = 'grey'

                #if row['training'] == 1:
                #    print(row['name'], 'training')
                #    c = 'blue'

                plt.title(year)
                plt.plot(*polygon.exterior.xy, color=c)

        #plt.show()
    # only return surge/not surge
    subset = result[['glacier_id', 'year', 'surging_rf']]

    return subset


def fillKnownSurges(data):
    # set surges to True in xarray dataset

    # load years
    years = data.year.values

    # create empty dictionary
    surges = {}

    # loop through years
    for year in years:
        # append empty list for each year
        surges[str(year)[:4]] = []

    # open csv file with surges between 2017 and 2022
    import csv
    with open('data/surge_table.csv', newline="") as csvfile:
        file = csv.reader(csvfile, delimiter=",")
        n = 0
        for row in file:
            # skip first row (column labels)
            if n == 0:
                n = n + 1
                continue

            # load id, start date and end date from csv file
            id = row[1]
            startyear = row[6]
            endyear = row[7]

            # if one of the surge start or surge end is not known
            if (startyear == "") | (endyear == ""):
                # if both dates are unknown
                if (startyear == "") & (endyear == ""):
                    # don't do anything
                    continue
                # if only start year is unknown
                elif (startyear == "") & (endyear != ""):
                    # and append glacier id to end year
                    if str(endyear)[:4] != "2017":
                        surges[str(endyear)[:4]].append(id)
                # if the other way around
                elif (startyear != "") & (endyear == ""):
                    #  append glacier id to start year
                    if str(startyear)[:4] != "2017":
                        surges[str(startyear)[:4]].append(id)

            # if both start year and end year are known
            if (startyear != "") & (endyear != ""):
                r = float(endyear) - float(startyear)
                y = float(startyear)
                for dy in range(0, int(r)):
                    y = y + dy
                    if (y > 2017) & (y < 2023):
                        surges[str(y)[:4]].append(id)

    for year in surges:
        for glacier in surges[year]:
            if glacier in list(data["glacier_id"].values):
                data["surging"].loc[{"year": int(year), "glacier_id": glacier}] = True

    return data


def createTrainingDataset(data):
    # create dataset with only surging glaciers
    surging_glaciers = data.where((data["surging_rf"] == True) | (data['glacier_id'] == 'G018079E77679N') |
                                  (data['glacier_id'] == 'G017944E77626N') | (data['glacier_id'] == 'G017525E77773N' ))
    surging_glaciers.dropna(subset=['surging_rf'], inplace=True)

    # add data for glaciers that are not surging

    return surging_glaciers


def thresholdAnalysis(df):

    print(df)
    df['surging_threshold'] = -1

    thresholds = {
        "max_dh": 25,
        "slope": 0,
        "slope_binned": 0,
        "slope_lower": 0,
        "bin_avg": 20
    }

    df_slope = df[['name', 'year', 'geom', 'glacier_id', 'slope', 'slope_binned', 'slope_lower', 'surging_threshold']].dropna()
    df_slope.loc[df_slope['slope'] < 0, 'surging_threshold'] = 1
    df_slope.loc[df_slope['slope'] > 0, 'surging_threshold'] = 0

    for index, row in df.iterrows():

        if (row['slope'] < 0) | (row['slope_binned'] < 0) | (row['slope_lower'] < 0) | (row['max_dh'] > 15):
            if ((row['slope'] < 0) | (row['slope_binned'] < 0) | (row['slope_lower'] < 0)) & (row['max_dh'] > 15):
                df.loc[df['dh_path'] == row['dh_path'], 'surging_threshold'] = 2
            else:
                df.loc[df['dh_path'] == row['dh_path'], 'surging_threshold'] = 1
        else:
            df.loc[df['dh_path'] == row['dh_path'], 'surging_threshold'] = 0



    for year in [2018, 2019, 2020, 2021, 2022, 2023]:
        print(year)
        for index, row in df.iterrows():
            if row['year'] == year:
                polygon = shapely.wkt.loads(row['geom'])
                if row['surging_threshold'] == 1:
                    print(row['name'], 1)
                    c = 'red'
                elif row['surging_threshold'] == 2:
                    print(row['name'], 1)
                    c = 'orange'
                elif row['surging_threshold'] == 0:
                    print(row['name'], 1)
                    c = 'blue'
                else:
                    print(row['name'], -1)
                    c = 'grey'

                #if row['training'] == 1:
                #    print(row['name'], 'training')
                #    c = 'blue'

                plt.title(year)
                plt.plot(*polygon.exterior.xy, color=c)

        plt.show()

    return df_slope


def uncertainty(dem, icesat, shp):

    shp = gpd.read_file('../data/reference_rectangles.shp').to_crs(32633)



