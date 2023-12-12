import os
from pathlib import Path
import socket
import pandas as pd
import sys
import xarray as xr
import numpy as np

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ[
        "PROJ_DATA"] = "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

sys.path += ["../ADSvalbard", "../projectfiles"]
import adsvalbard.rasters
from svalbardsurges import plotting
from svalbardsurges import analysis
from svalbardsurges import download
from svalbardsurges import build_dem
from svalbardsurges.inputs import dems
from svalbardsurges.inputs import shp
from svalbardsurges.inputs import icesat
from svalbardsurges.inputs import read_icesat
import svalbardsurges.controllers


def main():
    # CHOOSE VARIABLES
    # for datasets we want to be working with
    # ---------------------------------------

    # ICESat-2 download specifications
    icesat_product = 'ATL08'  # or ATL06 or ATL03
    date_range = ['2018-10-14', '2023-11-10']
    icesat_filepath = Path(f'data/icesat_{icesat_product}.nc')
    glacier_inventory = 'rgi'  # 'rgi' or 'gao'. will assign download url and filenames accordingly
    area = "svalbard"

    bboxes = {"svalbard": [5, 75, 40, 82], "heerland": [15.7, 77.35, 18.6, 78]}
    spatial_extent = bboxes[area]

    # ------------------------------------------------------------------------
    # CHOOSE ALGORITHMS
    # choose which parts of code will be run and which not (True = will be run, False = will not be run)
    # ------------------------------------------------------------------------

    # todo as global variables?
    hypso = True  # hypsometric binning
    ransac = False  # RANSAC analysis
    linearregression = True
    kmeans = False
    leastsquares = False
    validate = False  # validation of dh from icesat compared to arcticdem

    testdata = True  # use test d
    if testdata:
        icesat_filepath = Path('nordenskiold_land-is2.nc')

    # ------------------------------------------------------------------------
    # CREATE DIRECTORIES
    # which will be used for caching/saving data
    # ------------------------------------------------------------------------
    if not os.path.isdir("cache/"):  # caching
        os.mkdir("cache/")

    if not os.path.isdir("figures/"):  # folder for figures (saving plots)
        os.mkdir("figures/")

    if not os.path.isdir('data/'):  # saving main datasets (glacier outlines, dem, icesat)
        os.mkdir('data/')

    if not os.path.isdir("cache/shapefiles"):  # caching
        os.mkdir("cache/shapefiles")

    # --------------------------------------------------------
    # DOWNLOAD DATA
    # --------------------------------------------------------

    # DOWNLOAD ICESAT-2
    # using icepyx. data product is selected at beginning of code.
    download.download_icesat(
        data_product=icesat_product,
        spatial_extent=spatial_extent,
        date_range=date_range
    )

    # save as netcdf
    read_icesat.read(icesat_product, icesat_filepath)

    # BUILD DEM MOSAIC from NPI (function from Erik)
    # dem_mosaic_path = build_dem.build_npi_mosaic(verbose=True)

    bounds = build_dem.get_bounds('svalbard', [5, 5])
    dem_mosaic_path = adsvalbard.rasters.build_npi_mosaic(bounds, verbose=True)

    # DOWNLOAD GLACIER INVENTORY (RGI or GAO)
    # variables for chosen inventory
    if glacier_inventory == 'rgi':
        glacinv_url = 'https://api.npolar.no/dataset/f6afca5c-6c95-4345-9e52-cfe2f24c7078/_file/' \
                      '3df9512e5a73841b1a23c38cf4e815e3'
        glacinv_filepath = Path('data/rgi.zip')
    if glacier_inventory == 'gao':
        glacinv_url = 'https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v7/regional_files/' \
                      'RGI2000-v7.0-G/RGI2000-v7.0-G-07_svalbard_jan_mayen.zip'
        glacinv_filepath = Path('data/gao.zip')

    # download glacier inventory, function from Erik
    download.download_file(
        url=glacinv_url,
        filename=glacinv_filepath.name,
        directory=glacinv_filepath.parent
    )

    # choose glacier ids
    ids = False  # 'surging' or 'gao' or 'rgi' or 'auto' or 'surging' or 'all'

    # list of glacier IDs based on selected inventory
    # todo test the results on these two glacier inventories (on the same glaciers)
    if glacier_inventory == 'gao':
        glacier_ids = [
            # 12412,      # Storbreen
            13406.1,  # Scheelebreen
            13218.1,  # Doktorbreen
            # 17310.1,    # Hinlopenbreen
            # 15511.1     # Kongsbreen
        ]

    if glacier_inventory == 'rgi':
        glacier_ids = [
            "G018031E77579N",  # Kvalbreen
            'G016964E77694N',  # Scheelebreen
            'G017525E77773N',
            'G017911E77804N',
            'G016885E77574N',
            'G016172E77192N',  # Storbreen
            'G018042E78675N',   # Negribreen
            'G017497E78572N',     # Tunabreen
            'G023559E79453N',
            'G016807E77171N',
            'G015026E77342N',
            'G013095E79037N',
            'G025297E79771N',
            'G016482E76791N'
        ]

    # determine name of ID attribute based on chosen glacier inventory
    if glacier_inventory == 'rgi':
        id_attr = 'glims_id'
    if glacier_inventory == 'gao':
        id_attr = 'IDENT'

    # loop through all the glaciers in dataset
    # glacier_ids = shp.getIDs(glacinv_filepath, id_attr)

    # select glaciers inside bounding box (spatial extent)
    glacier_ids = shp.withinBBox(spatial_extent, glacinv_filepath, id_attr, Path(f'cache/{area}_{glacier_inventory}.shp'))

    if ids == 'surging':
        glacier_ids = [
            "G017158E77876N",
            "G016885E77574N",
            "G017333E77537N",
            "G017400E77460N",
            "G018031E77579N",
            "G017697E77678N",
            "G016964E77694N"
        ]

    surging_glaciers = []

    # --------------------------------------------------------------------
    # START OF ACTUAL CODE
    # --------------------------------------------------------------------
    # loop through all the glaciers
    # save pandas to csv todo cache
    # cache of whole results thing
    resultspath = Path('cache/df_results.csv')
    if not resultspath.is_file():
        gl_sum = len(glacier_ids)
        print(gl_sum)

        # add years as int, figure out how many years in data
        icesat_path, years = icesat.yearsInData(icesat_filepath)

        bins = np.array([0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100])  # todo better bins

        # create empty xarray dataset
        results = xr.Dataset()
        # create coordinates of dataset
        results.coords["year"] = "year", np.arange(years[0], years[-1] + 1)
        results.coords["glacier_id"] = "glacier_id", glacier_ids
        #results.coords["bin"] = "bin", bins[1:]
        # create data variables
        results["geom"] = "glacier_id", np.full(gl_sum, 0, dtype=object)
        results["name"] = "glacier_id", np.full(gl_sum, 0, dtype=object)
        #results["avg_dh"] = ("year", "glacier_id", "bin"), np.zeros((len(years) - 1, gl_sum, len(bins[1:])))
        #results["count"] = ("year", "glacier_id", "bin"), np.zeros((len(years) - 1, gl_sum, len(bins[1:])))
        results["slope"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["intercept"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["max_dh"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["bin_max"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["surging"] = ("year", "glacier_id"), np.empty((len(years), gl_sum)) == 0  # returns bool false

        # loop through years
        for year in years:
            print(year)
            # group by hydrological year
            data_path = analysis.groupByHydroYear(icesat_path, year)

            # count dh on hydro year
            data_dh_path = analysis.icesatDEMDifference(data_path, dem_mosaic_path[0],
                                                        Path(f'cache/icesat{year}dh.nc'))

            n = 0
            for glacier_id in glacier_ids:
                print(glacier_id)
                n = n + 1
                # load glacier outline
                glacier_outline = shp.load_shp(
                    file_path=str(glacinv_filepath),
                    id_attribute=id_attr,
                    glacier_id=glacier_id)

                # determine NAME column in attribute table
                if glacier_inventory == 'rgi':
                    glacier_name = glacier_outline.glac_name.iloc[0]
                elif glacier_inventory == 'gao':
                    glacier_name = glacier_outline.NAME.iloc[0]

                if glacier_name == None:
                    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name, glacier_outline.iloc[0]["geometry"])
                    #print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, "nodata")
                    continue

                # correct names
                if "?" in glacier_name:
                    glacier_name = glacier_name.replace("?", "")
                if " " in glacier_name:
                    glacier_name = glacier_name.replace(" ", "")
                if "/" in glacier_name:
                    glacier_name = glacier_name.replace("/", "")

                # skip glacier if area smaller than 11 km2 (but append to results)
                if glacier_outline.geometry.area.iloc[0] / 1e6 < 15:
                    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name, glacier_outline.iloc[0]["geometry"])
                    #print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, "nodata")
                    continue

                # todo some statistical analysis of data - if i actually have enough data for the analysis
                # if all data is clustered then throw it out

                # compute bounds of glacier outline
                spatial_extent = dict(zip(['left', 'bottom', 'right', 'top'], glacier_outline.total_bounds))

                # create directory for saving figures for each glacier separately
                if not os.path.isdir(f"figures/{glacier_id}"):
                    os.mkdir(f"figures/{glacier_id}")
                if not os.path.isdir(f"figures/{glacier_id}/{glacier_inventory}"):
                    os.mkdir(f"figures/{glacier_id}/{glacier_inventory}")

                # subset data to glacier outline
                subset = icesat.icesatSpatialSubset(input_path=data_dh_path, spatial_extent=spatial_extent,
                                                    glacier_outline=glacier_outline,
                                                    output_path=Path(f"cache/{glacier_name}{year}{glacier_inventory}.nc"))

                # if the dataset is empty then don't run the analysis
                if type(subset) == str:
                    # append information about empty subset to results and skip running the analysis
                    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name, glacier_outline.iloc[0]["geometry"])
                    #print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, "nodata")
                    continue

                # do max dh in lower part
                lower_part = subset.where(subset.h < 400, drop=True)
                if lower_part.index.size < 10:
                    results["max_dh"].loc[{"year": year, "glacier_id": glacier_id}] = np.nan
                else:
                    max_dh = np.percentile(lower_part.dh.values, 90)
                    results["max_dh"].loc[{"year": year, "glacier_id": glacier_id}] = max_dh

                plotting.plotYearlyDH(
                    icesat_data=subset, glacier_outline=glacier_outline, glacier_name=glacier_name, glacier_id=glacier_id,
                    output_path=Path(
                        f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_yearlydh_{glacier_inventory}_{icesat_product}.png')
                )

                # todo plots at the end (if pltshow)
                plotting.plotElevationPts(subset, glacier_name)

                # hypsometric binning of glacier
                try:
                    hypso = analysis.icesatHypso(
                        icesat_data=subset,
                        bins=bins,
                    )
                except:
                    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name, glacier_outline.iloc[0]["geometry"])
                    #print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, "nodata")
                    continue

                # append values and counts from hypso bins to results df
                #values = hypso["value"].values
                #counts = hypso["count"].values

                #for i in range(0, len(bins)-1):
                #    results["avg_dh"].loc[{"year": year, "glacier_id": glacier_id, "bin": bins[i+1]}] = values[i]
                #    results["count"].loc[{"year": year, "glacier_id": glacier_id, "bin": bins[i+1]}] = counts[i]

                bin_max = max(hypso["value"][4:])
                results["bin_max"].loc[{"year": year, "glacier_id": glacier_id}] = bin_max

                # count slope and intercept
                slope, intercept = analysis.linRegHypso(hypso)

                # append values to results
                results["slope"].loc[{"year": year, "glacier_id": glacier_id}] = slope
                results["intercept"].loc[{"year": year, "glacier_id": glacier_id}] = intercept
                results["geom"].loc[{"glacier_id": glacier_id}] = glacier_outline.iloc[0]["geometry"]
                results["name"].loc[{"glacier_id": glacier_id}] = glacier_name
                results["surging"].loc[{"year": year, "glacier_id": glacier_id}] = False

                print(glacier_name, glacier_id, f'{n}/{gl_sum}', year)

                # plot hypsometric curves and yearly dh for glacier
                plotting.plotHypso(
                    data=hypso,
                    glacier_id=glacier_id,
                    glacier_name=glacier_name,
                    glacier_area=glacier_outline.geometry.area.iloc[0] / 1e6,
                    output_path=Path(
                        f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_hypso_{glacier_inventory}-{icesat_product}.png')
                )

        # change surge values to True for known surges
        results = analysis.fillKnownSurges(results)

        # convert xarray dataset to pandas dataframe
        df = results[["glacier_id", "name", "slope", "intercept", "max_dh", "bin_max", "surging", "geom"]].to_dataframe().reset_index()
        df.to_csv('cache/df_results.csv')

    # load cached data
    df = pd.read_csv(resultspath)

    # create training dataset
    training_dataset = analysis.createTrainingDataset(df)

    # classify using random forest
    analysis.classifyRF(df, training_dataset)

    # do a threshold analysis
    #analysis.thresholds(df)

    # todo convert pandas dataframe to shapefile

    # visualize results
    #plotting.plotSurges('none', results)

    for glacier_id in glacier_ids:
        # -------------------------------------------------------------
        # VALIDATION OF RESULTS
        # with arcticdem
        # -------------------------------------------------------------
        if validate:
            # todo validation in loop above
            # path to ArcticDEM directory
            arcticdem_dir = Path('arcticdem/')
            arcticdems = {}

            # subset ArcticDEM rasters to glacier boundary
            for file in os.listdir(arcticdem_dir):
                year = os.path.split(file)[1][-8:-4]

                arcticdem_subset_path = dems.load_dem(
                    input_path=arcticdem_dir / file,
                    spatial_extent=spatial_extent,
                    label=f'arcticdem_{glacier_name}_{glacier_inventory}_{year}')

                arcticdem_masked_path = dems.mask_dem(
                    dem_path=arcticdem_subset_path,
                    glacier_outline=glacier_outline,
                    label=f'arcticdem_{glacier_name}_{glacier_inventory}_{year}')

                arcticdems[year] = arcticdem_masked_path

            # hypsometric bins
            #arcticdem_hypso = analysis.hypso_dem(
            #    dems=arcticdems,
            #    bins=bins,
            #    ref_dem=dem_masked_path
            #)

            print(f'{glacier_name} validation without errors.')

            # plot hypso curves
            #plotting.plot_hypso_arcticdem(
            #    data=arcticdem_hypso,
            #    glacier_id=glacier_id,
            #    glacier_name=glacier_name,
            #    glacier_area=glacier_outline.area.iloc[0] / 1e6,
            #    output_path=Path(
            #        f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_ademhypso_{glacier_inventory}.png')
            #)

            # plot elevation differences
            #for year in arcticdems:
            #    if year != '2022':
            #        plotting.plot_arcticDEM_dh(
            #            data=arcticdems,
            #            ref_dem_path=dem_masked_path,
            #            year=year,
            #            glacier_outline=glacier_outline,
            #            glacier_name=glacier_name,
            #            glacier_id=glacier_id,
            #            output_path=Path(
            #                f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_ademhypso{year}_{glacier_inventory}.png')
            #        )


if __name__ == "__main__":
    main()
