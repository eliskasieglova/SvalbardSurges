import xarray as xr
import numpy as np
import warnings
import rasterio as rio
from matplotlib import pyplot as plt
from sklearn import datasets, linear_model

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

    return bins


def icesatHypso(input_path, bins, surgenosurge):
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
                return hypso_bins, surgenosurge

            # append data to dictionary
            hypso_bins[year] = hypso

            # if surge, append 1 to results, if not surge append 0 to results
            if hypso_bins[year].iloc[0].value > 20:
                surgenosurge[year]['hypso'] = 1

            else:
                surgenosurge[year]['hypso'] = 0

    return hypso_bins, surgenosurge


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

def ransac_alg(data, thresholds, glacier_name, pltshow, pltsave):
    """

    Params
    ------
    - data
        xarray
    - thresholds
        list containing two values: [low threshold, high threshold]

    """
    # todo return df with ransac coefficients for all the elevation bins

    # split data between thresholds
    icesat_high = data.where(data.h > thresholds[1], drop=True)
    icesat_mid = data.where((data.h > thresholds[0]) & (data.h < thresholds[1]), drop=True)
    icesat_low = data.where(data.h < thresholds[0], drop=True)

    datasets = [icesat_high, icesat_mid, icesat_low]

    # if no data for given year
    if data.index.size == 0:
        return -999

    year = max(data.year_int.values)

    # create with subplots and title
    plt.subplots(1, 3, sharey=True)
    #plt.xticks([20180000, 20220000])
    plt.suptitle(f'{str(year-1)[:4]}-{str(year)[:4]}, {glacier_name}')


    lw = 2 # linewidth for plots

    coefficients = []

    i = 1
    for data in datasets:
        # RANSAC from scikit.learn documentation
        # x-axis = time, y-axis = dh
        # so what we are comparing is not differences between years but differences between given year and 2010 (DEM)

        # reshape arrays
        X = data.h.values.reshape(-1, 1)
        y = data.dh.values.reshape(-1, 1)

        # Fit line using all data
        #lr = linear_model.LinearRegression()
        #lr.fit(X, y)

        # Robustly fit data with ransac algorithm
        ransac = linear_model.RANSACRegressor(max_trials=100)

        # try except for if there is not enough samples
        try:
            ransac.fit(X, y)
        except:
            return 0

        inlier_mask = ransac.inlier_mask_
        outlier_mask = np.logical_not(inlier_mask)

        # Predict data of estimated models
        line_X = np.arange(X.min(), X.max())[:, np.newaxis]
        #line_y = lr.predict(line_X)
        line_y_ransac = ransac.predict(line_X)

        # Compare estimated coefficients
        #print("Estimated coefficients (true, linear regression, RANSAC):")
        #print(coef, lr.coef_, ransac.estimator_.coef_)

        # PLOT based on if it's high or low
        plt.subplot(1, 3, i)
        plt.scatter(
            X[inlier_mask], y[inlier_mask], color="yellowgreen", marker=".", label="Inliers"
        )
        plt.scatter(
            X[outlier_mask], y[outlier_mask], color="gold", marker=".", label="Outliers"
        )
        #plt.plot(line_X, line_y, color="navy", linewidth=lw, label="Linear regressor")
        plt.plot(
            line_X,
            line_y_ransac,
            color="cornflowerblue",
            linewidth=lw,
            label="RANSAC regressor",
        )

        if i == 1:
            t = f'>{thresholds[1]}m'

        elif i == 2:
            t = f'{thresholds[0]}-{thresholds[1]}m'

        elif i == 3:
            t = f'<{thresholds[0]}m'

        ransac_coef = ransac.estimator_.coef_[0][0]
        plt.title(f'{t}\n{str(ransac_coef)[:5]}')
        plt.xlabel("Input")
        plt.ylabel("Response")

        coefficients.append(ransac_coef)
        i = i + 1

    if pltshow:
        #plt.legend(loc="lower right")
        plt.show()

    plt.close()

    return ransac_coef

def ransac(icesat_path, surgenosurge, glacier_name, pltshow, pltsave):

    # load data
    data = xr.load_dataset(icesat_path)

    # todo: a better way to split based on statistics and stuff
    # for example lower 1/5, upper 1/5 and in between
    # or thirds
    # min, max, avg, median
    # figure out some statistics like lowest and highest point of glacier, elevation bins etc.
    # and based on that determine the thresholds
    thresholds = [200, 500]

    # loop through the years and do ransac both for high and low elevation
    years = np.unique(data.year_int.values)
    for year in years:
        if (year != years[-1]): # | (year != years[0]):
            subset = icesat.groupby_hydroyear(data, year)
            ransac_coef = ransac_alg(subset, thresholds, glacier_name, pltshow, pltsave)

            if ransac_coef > 0.5:
                surgenosurge[year]['ransac'] = 1

            else:
                surgenosurge[year]['ransac'] = 0

    return surgenosurge


def updateSurgeSum(df):

    for year in df:
        df[year]['sum'] = df[year]['hypso'] + df[year]['ransac']

    return df
