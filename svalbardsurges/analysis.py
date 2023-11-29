import xarray as xr
import numpy as np
import warnings
import rasterio as rio
from matplotlib import pyplot as plt
from sklearn import linear_model, metrics
from sklearn.cluster import KMeans, DBSCAN, SpectralClustering
from sklearn.mixture import GaussianMixture
from sklearn.model_selection import GridSearchCV
from matplotlib.patches import Ellipse
from scipy import linalg
from scipy.optimize import curve_fit
import pandas as pd


# Catch a deprecation warning that arises from skgstat when importing xDEM
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem

from svalbardsurges.inputs import icesat


def icesat_DEM_difference(dem_path, icesat_path, glacier_outline, output_path):
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

    # if subset already exists return path
    if output_path.is_file():
        return output_path

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

    # subtract ICESat-2 elevation from DEM elevation (with elevation correction) todo for each beam
    data["dh"] = data["h"] - data["dem_elevation"] - 31.55 # todo a bit better correction

    if data.dropna('index')['dh'].size == 0:
        return 'empty'

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


def icesatHypso(input_path, bins, surgenosurge, surgevalues, threshold):
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
    data = xr.open_dataset(input_path)

    # empty dictionary to append binned elevation differences by year
    hypso_bins = {}

    years = np.unique(data.year_int.values)

    for year in years:
        if year != years[-1]:
            y = year * 10000
            hydrosilvestr = y + 1031  # create hydrosilvestr, for example 20181031 (October 31st 2018)
            subset = data.where((data.date_int.values > hydrosilvestr) & (data.date_int.values <= hydrosilvestr+10000))
            year = year + 1

            try:
                hypso = xdem.volume.hypsometric_binning(
                    ddem=subset['dh'],
                    ref_dem=subset['dem_elevation'],
                    kind="custom",
                    bins=bins,
                    aggregation_function=np.nanmean
                )
            except:
                surgenosurge[year]['hypso'] = -999
                surgevalues[year]['hypso'] = -999
                return hypso_bins, surgenosurge, surgevalues

            # append data to dictionary
            hypso_bins[year] = hypso

            # append elevation change in lower part of glacier to values df
            surgevalues[year]['hypso'] = hypso_bins[year].iloc[0].value

            # if surge, append 1 to results, if not surge append 0 to results
            if hypso_bins[year].iloc[0].value > threshold:
                surgenosurge[year]['hypso'] = 1
            else:
                surgenosurge[year]['hypso'] = 0

    return hypso_bins, surgenosurge, surgevalues


def evaluateHypso(hypso, pltshow):
    # todo least squares, figure out other means of identifying outliers (surges)
    # todo leave evaluating, move plotting
    if pltshow:
        # intitiate plot
        plt.subplots(2, 2)

        i = 1
        # loop through years in hypso dictionary
        for year in hypso:
            # call subplot
            ax = plt.subplot(2, 2, i)

            # prepare data
            x = hypso[year].index.mid
            y = hypso[year].value

            # remove Nans from list
            x, y = removeNans(x, y)

            # now try to put a curve through it
            from scipy.optimize import curve_fit
            parameters, covariance = curve_fit(Gauss, x, y) # todo least squares
            fit_A = parameters[0]
            fit_B = parameters[1]

            fit_y = Gauss(y, fit_A, fit_B)

            # plot data
            plt.scatter(x, y, color='orange', marker='.')  # points
            plt.plot(x, fit_y, '-', label='fit')  # curve

            # linear regression scikit
            x = x.reshape(-1, 1)
            y = y.reshape(-1, 1)
            lr = linear_model.LinearRegression()
            lr.fit(x, y)

            line_X = np.arange(x.min(), x.max())[:, np.newaxis]
            line_y = lr.predict(line_X)

            # plot
            plt.plot(line_X, line_y, color="navy", linewidth=2, label="Linear regressor")

            # coefficient
            coef = lr.coef_[0][0]


            # polynomial regression
            x = x.reshape(1, -1)
            y = y.reshape(1, -1)
            x = x.tolist()
            y = y.tolist()

            x = x[0]
            y = y[0]

            poly_fit = np.poly1d(np.polyfit(x, y, 2))
            xx = [0, 50, 100, 150, 200, 250, 300, 350, 400, 450, 500,550, 600, 650, 700, 750, 800, 850, 900, 950, 1000, 1050, 1100]
            plt.plot(xx, poly_fit(xx), c='r', linestyle='-')

            # invert x-axis to start with bigger values on the left
            ax.invert_xaxis()
            i=i+1

        plt.show()
    return


def removeNans(x, y):
    x = x.tolist()
    y = y.tolist()
    a = x
    b = y
    # todo describe function
    # go through elements of list
    unwanted = []
    for i in range(len(y)):
        # if value is nan, then remove the value from the list (don't plot, doesn't go in the analysis)
        if not y[i] < 10000:  # todo IMPROVE (this is a very quick and ugly fix for getting rid of nans)
            unwanted.append(i)

    # delete the unwanted nans (based on index)
    for i in sorted(unwanted, reverse=True):
        del x[i]
        del y[i]

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

    print('ransac done')
    return hypso

def regressionAlg(algorithm, data, glacier_name, pltshow, pltsave):
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
        return -999

    year = max(data.year_int.values)

    plt.suptitle(f'{str(year - 1)[:4]}-{str(year)[:4]}, {glacier_name}, {algorithm}')

    lw = 2  # linewidth for plots

    # reshape arrays
    X = data.h.values.reshape(-1, 1)
    y = data.dh.values.reshape(-1, 1)

    if algorithm == "linreg":
        # Fit line
        lr = linear_model.LinearRegression()
        lr.fit(X, y)

        line_X = np.arange(X.min(), X.max())[:, np.newaxis]
        line_y = lr.predict(line_X)

        # plot
        plt.scatter(X, y, color="yellowgreen", marker='.')
        plt.plot(line_X, line_y, color="navy", linewidth=lw, label="Linear regressor")

        # coefficient
        coef = lr.coef_[0][0]

    # RANSAC
    if algorithm == "ransac":
        # Robustly fit data with ransac algorithm
        ransac = linear_model.RANSACRegressor(max_trials=100)
        ransac.fit(X, y)

        inlier_mask = ransac.inlier_mask_
        outlier_mask = np.logical_not(inlier_mask)

        # Predict data of estimated models
        line_X = np.arange(X.min(), X.max())[:, np.newaxis]
        line_y_ransac = ransac.predict(line_X)

        # PLOT
        plt.scatter(X[inlier_mask], y[inlier_mask], color="yellowgreen", marker=".", label="Inliers")
        plt.scatter(X[outlier_mask], y[outlier_mask], color="gold", marker=".", label="Outliers")
        plt.plot(line_X, line_y_ransac, color="cornflowerblue", linewidth=lw, label="RANSAC regressor")

        # ransac coefficient
        coef = ransac.estimator_.coef_[0][0]

    plt.title(f'{str(year - 1)[:4]}-{str(year)[:4]}, {glacier_name}, {algorithm}, {coef}')
    plt.xlabel("Input")
    plt.ylabel("Response")

    if pltshow:
        plt.show()

    return coef

def regression(algorithm, icesat_path, surgenosurge, surgevalues, threshold, glacier_name, pltshow, pltsave):

    # load data
    data = xr.load_dataset(icesat_path)

    # group by hydrological years
    years = np.unique(data.year_int.values)
    for year in years:
        if (year != years[-1]): # | (year != years[0]):
            subset = icesat.groupby_hydroyear(data, year)
            coef = regressionAlg(algorithm, subset, glacier_name, pltshow, pltsave)

            # append coefficient to values df
            surgevalues[year][algorithm] = coef

            # update 1 or 0 for surge/not surge based on chosen threshold
            if coef > threshold:
                surgenosurge[year][algorithm] = 1
            else:
                surgenosurge[year][algorithm] = 0

    return surgenosurge, surgevalues


def updateSurgeSum(df):

    for year in df:
        df[year]['sum'] = df[year]['hypso'] + df[year]['ransac']

    return df

def clusterAnalysis(icesat_path, surgenosurge, surgevalues, glacier_name, pltshow, pltsave,
                    dbscan=True, kmeans=False, gaussianmixture=False, spectralclustering=False):

    """
    i dont think a cluster analysis is the way to go - usually the surge is only a couple of points
    and it is not really "deconnected" from the rest of the data points so the pts are usually
    either considered outliers (not it any cluster) or connected with other pts that are not
    part of the surge
    """

    # load data
    data = xr.open_dataset(icesat_path)

    # subset only lower half of the glacier
    middle = (max(data['h']) + min(data['h']))/2
    data = data.where(data['h'] < middle)

    plt.subplots(2, 2)

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

            plt.subplot(2, 2, i)
            if dbscan:
                algDBSCAN(X, 2)  # todo what if there is too many holes in data so it does not identify the surge as a cluster?

            if gaussianmixture:
                algGaussianMixture(X)

            if kmeans:
                algKMeans(X)

            if spectralclustering:
                algSpectralClustering(X)


            i = i + 1
    plt.tight_layout()
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

def leastSquares(icesat_path):
    # least squares on lower part of dataset

    # load data
    data = xr.open_dataset(icesat_path)

    # subset
    #middle = (min(data['h']) + max(data['h']))/2
    #data = data.where(data['h']<middle)

    plt.subplots(2, 2)
    # group by hydrological years
    years = np.unique(data.year_int.values)
    i = 1
    for year in years:
        if (year != years[-1]):  # | (year != years[0]):
            if i == 5:
                continue
            subset = icesat.groupby_hydroyear(data, year)
            x = subset['h']
            y = subset['dh']

            alpha = curve_fit(lsFun, xdata=x, ydata=y)[0]
            print(alpha)

            # plot
            plt.subplot(2, 2, i)
            plt.scatter(subset['h'], subset['dh'])
            plt.plot(x, alpha[0] * x + alpha[1], 'r')

        i = i + 1
    plt.show()

    # todo move plotting
    # todo return 1/0 surge/notsurge

    return


def lsFun(x, a, b):
    y = a*x + b
    return y


# todo spectral clustering BIRCH, others?
# https://scikit-learn.org/stable/auto_examples/cluster/plot_cluster_comparison.html#sphx-glr-auto-examples-cluster-plot-cluster-comparison-py
