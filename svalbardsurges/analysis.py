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

    icesat = xr.open_dataset(icesat_path)

    with rio.open(dem_path) as raster, warnings.catch_warnings():
        warnings.filterwarnings('ignore', message='.*converting a masked element to nan.*')
        icesat["dem_elevation"] = "index", np.fromiter(
            raster.sample(
                np.transpose([icesat.easting.values, icesat.northing.values]),
                masked=True
            ),
            dtype=raster.dtypes[0],
            count=icesat.easting.shape[0]
        )

    # subtract ICESat-2 elevation from DEM elevation (with elevation correction)
    icesat["dh"] = icesat["h"] - icesat["dem_elevation"] - 31.55

    # save as netcdf file
    icesat.to_netcdf(output_path)

    return output_path

def create_bins(data_path):

    # open data
    data = xr.open_dataset(data_path)

    bins = np.nanpercentile(data["dem_elevation"], np.linspace(0, 100, 6))

    return bins

def hypso_is2(input_path, bins):
    """
    Hypsometric binning of glacier elevation changes.

    Parameters
    ----------
    - input_path
        path to IS2 dataset containing the variables 'dh' and 'dem_elevation'
    - bins

    Results
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
            hydrosilvestr = y + 1031  # create hydrosilvestr, for example 20181031 (october 31st 2018)
            subset = data.where((data.date_int.values > hydrosilvestr) & (data.date_int.values <= hydrosilvestr+10000))

            hypso = xdem.volume.hypsometric_binning(
                ddem=subset['dh'],
                ref_dem=subset['dem_elevation'],
                kind="custom",
                bins=bins,
                aggregation_function=np.nanmean
            )

            # append data to dictionary
            hypso_bins[year] = hypso

    #for year, data_subset in data.groupby(data["date"].dt.year):
    #    # todo: group the data by hydrological years
    #    # create hypsometric bins
    #    hypso_subset = xdem.volume.hypsometric_binning(
    #        ddem=data_subset['dh'],
    #        ref_dem=data_subset['dem_elevation'],
    #        kind="custom",
    #        bins=bins,
    #        aggregation_function=np.nanmean
    #    )

        # append data to dictionary
        #hypso_bins[year] = hypso

    return hypso_bins

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

    Results
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

def ransac1(icesat_path):


    # split data into subsets by elevation (top of glacier/terminus)
    # todo: a better way to split based on statistics and stuff
    icesat_high = data.where(data.h > high_threshold, drop=True)
    icesat_low = data.where(data.h < low_threshold, drop=True)
    #icesat_mid = data.where(data.h < high_threshold & data.h > low_threshold)

    # do RANSAC on high
    # x-axis = time, y-axis = dh
    l = [icesat_high, icesat_low]
    years = np.unique(data.year_int.values)
    for year in years:
        for i in range(1):
            data = l[i]
            if year != years[-1]:
                data = icesat.groupby_hydroyear(data, year, 1031)

                # based on tutorial from scikit.learn
                X = data.date_int.values.reshape(-1, 1) # reshape arrays
                y = data.dh.values.reshape(-1, 1)

                # Fit line using all data
                lr = linear_model.LinearRegression()
                lr.fit(X, y)

                # Robustly fit data with ransac algorithm
                ransac = linear_model.RANSACRegressor()
                ransac.fit(X, y)
                inlier_mask = ransac.inlier_mask_
                outlier_mask = np.logical_not(inlier_mask)

                # Predict data of estimated models
                line_X = np.arange(X.min(), X.max())[:, np.newaxis]
                line_y = lr.predict(line_X)
                line_y_ransac = ransac.predict(line_X)

                # Compare estimated coefficients
                #print("Estimated coefficients (true, linear regression, RANSAC):")
                #print(coef, lr.coef_, ransac.estimator_.coef_)

                # plot
                lw = 2
                plt.scatter(
                    X[inlier_mask], y[inlier_mask], color="yellowgreen", marker=".", label="Inliers"
                )
                plt.scatter(
                    X[outlier_mask], y[outlier_mask], color="gold", marker=".", label="Outliers"
                )
                plt.plot(line_X, line_y, color="navy", linewidth=lw, label="Linear regressor")
                plt.plot(
                    line_X,
                    line_y_ransac,
                    color="cornflowerblue",
                    linewidth=lw,
                    label="RANSAC regressor",
                )
                plt.legend(loc="lower right")
                if i == 0:
                    plt.title(f'elevation above {high_threshold}')

                elif i == 1:
                    plt.title(f'elevation below {low_threshold}')

                plt.xlabel("Input")
                plt.ylabel("Response")
                plt.show()

    # todo: return coefficients
    return

def ransac(icesat_path):
    # todo: add pd dataframe as input and output

    # load data
    data = xr.load_dataset(icesat_path)

    # figure out some statistics like lowest and highest point of glacier, elevation bins etc.
    # and based on that determine the thresholds
    high_threshold = 500
    low_threshold = 200

    # split the data for each year
    # loop through the years and do ransac both for high and low elevation

    return

