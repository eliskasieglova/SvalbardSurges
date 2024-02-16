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
from svalbardsurges import plotting as plotting
from svalbardsurges import analysis
from svalbardsurges import download
from svalbardsurges import build_dem
from svalbardsurges.inputs import dems
from svalbardsurges.inputs import shp
from svalbardsurges.inputs import icesat
from svalbardsurges.inputs import read_icesat


def main():
    # CHOOSE VARIABLES
    # for datasets we want to be working with
    # ---------------------------------------

    # ICESat-2 download specifications
    icesat_product = 'ATL06'  # ATL06 or ATL08
    date_range = ['2018-10-14', '2023-11-10']
    icesat_filepath = Path(f'data/icesat_{icesat_product}.nc')
    area = "svalbard"

    bboxes = {"all": [0, 70, 55, 90],
              "svalbard": [5, 75, 40, 82],
              "heerland": [15.7, 77.35, 18.6, 78],
              "south": [5, 75, 40, 78],
              "northwest": [10.72, 78.11, 15.6, 80.09],
              "northeast": [15.49, 78.02, 22.77, 80.13],
              "nordaustland": [17.86, 79.25, 35.63, 80.43],
              "barentsoya": [19.49, 77.21, 24.99, 78.61]
              }

    spatial_extent = bboxes[area]

    # ------------------------------------------------------------------------
    # CHOOSE ALGORITHMS
    # choose which parts of code will be run and which not (True = will be run, False = will not be run)
    # ------------------------------------------------------------------------

    from svalbardsurges.controllers import testdata, validate, rerun
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
    glacier_inventory = 'rgi'
    glacinv_url = 'https://api.npolar.no/dataset/f6afca5c-6c95-4345-9e52-cfe2f24c7078/_file/' \
                  '3df9512e5a73841b1a23c38cf4e815e3'
    glacinv_filepath = Path('data/rgi.zip')
    id_attr = 'glims_id'

    # download glacier inventory, function from Erik
    download.download_file(
        url=glacinv_url,
        filename=glacinv_filepath.name,
        directory=glacinv_filepath.parent
    )

    # select glaciers inside bounding box (spatial extent)
    #glacier_ids = shp.withinBBox(bboxes['all'], glacinv_filepath, id_attr, Path(f'data/{area}_{glacier_inventory}.shp'))

    glacier_ids = shp.listIDs(glacinv_filepath)
    # --------------------------------------------------------------------
    # START OF ACTUAL CODE
    # --------------------------------------------------------------------

    # todo what about glaciers that do not end at sea level

    # if results file does not exist do the analysis
    if rerun:
        # count glacier sum
        gl_sum = len(glacier_ids)
        print(gl_sum)

        # add years as int, figure out how many years in data
        if testdata:
            output_path = Path(f'data/testdata_years.nc')
        else:
            output_path = Path(f'data/icesat{icesat_product}.nc')
        icesat_path, years = icesat.yearsInData(icesat_filepath, output_path)
        print(years)

        # set elevation bins
        bins = np.array([0, 100, 200, 300, 400, 500, 600, 700, 800, 900, 1000, 1100])  # todo better bins

        # create empty xarray dataset
        results = xr.Dataset()

        # create coordinates of dataset
        results.coords["year"] = "year", np.arange(years[0], years[-1] + 1)
        results.coords["glacier_id"] = "glacier_id", glacier_ids

        # create data variables
        results["geom"] = "glacier_id", np.full(gl_sum, -999, dtype=object)
        results["name"] = "glacier_id", np.full(gl_sum, -999, dtype=object)
        results["errormessage"] = ("year", "glacier_id"), np.full((len(years), gl_sum), 0, dtype=object)
        results["dh_path"] = ("year", "glacier_id"), np.full((len(years), gl_sum), 0, dtype=object)
        results["min_dh"] = ("year", "glacier_id"), np.full((len(years), gl_sum), -999)
        results["max_dh"] = ("year", "glacier_id"), np.full((len(years), gl_sum), -999)
        results["min_dh"] = ("year", "glacier_id"), np.full((len(years), gl_sum), -999)

        # create pt data variables
        results["h"] = ("year", "glacier_id"), np.full((len(years), gl_sum), -999, dtype=object)
        results["dh"] = ("year", "glacier_id"), np.full((len(years), gl_sum), -999, dtype=object)

        # create variables for results of analysis
        results["slope"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["slope_binned"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["slope_lower"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["intercept"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["max_dh"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["bin_max"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))



        # yearly change, not accumulated
        # --> we will only have yearly change from the second year in the dataset (2019??)
        results["slope_y"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["intercept_y"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["max_dh_y"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))
        results["bin_max_y"] = ("year", "glacier_id"), np.zeros((len(years), gl_sum))

        # surging parameter (boolean)
        results["surging_rf"] = ("year", "glacier_id"), np.empty((len(years), gl_sum)) == -999  # returns bool false
        results["surging_threshold"] = ("year", "glacier_id"), np.full((len(years), gl_sum), -1)

        # loop through years
        # do the difference for the whole dataset then loop through the years
        #if testdata:
        #    output_path = Path(f'data/testdata{area}_dh.nc')
        #else:
        #    output_path = Path(f'cache/{icesat_product}{area}dh.nc')

        output_path = Path(f'cache/{icesat_product}{area}dh.nc')
        data_dh_path = analysis.icesatDEMDifference(icesat_path, dem_mosaic_path[0], output_path)

        for year in years:
            print(year)
            # group by hydrological year
            output_path = Path(f'cache/{icesat_product}{area}{year}.nc')
            data_year_path = analysis.groupByHydroYear(data_dh_path, year, output_path)

            # visualize where the glaciers are and where the icesat data is
            #plotting.plotYears(glacier_ids, glacinv_filepath, data_year_path)

            from matplotlib import pyplot as plt

            n = 0
            for glacier_id in glacier_ids:
                print(glacier_id)
                n = n + 1

                # load glacier outline
                glacier_outline = shp.load_shp(
                    file_path=str(glacinv_filepath),
                    attr_name=id_attr,
                    attr_value=glacier_id)

                # mask dem
                #dem_subset_path = dems.mask_dem(dem_mosaic_path[0], glacier_outline.iloc[0]["geometry"], f'dem_{glacier_id}')

                # determine NAME column in attribute table
                if glacier_inventory == 'rgi':
                    glacier_name = glacier_outline.glac_name.iloc[0]
                elif glacier_inventory == 'gao':
                    glacier_name = glacier_outline.NAME.iloc[0]

                #if glacier_name == None:
                #    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name, glacier_outline.iloc[0]["geometry"])
                #    print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, "!!! name none")
                #    continue

                # correct names
                if glacier_name is None:
                    #errormessage = 'name is NoneType'
                    #icesat.fillWithNans(results, year, glacier_id, bins, glacier_name,
                    #                    glacier_outline.iloc[0]["geometry"], errormessage)

                    #print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, errormessage)
                    #continue
                    glacier_name = f'None{n}'

                if "?" in glacier_name:
                    glacier_name = glacier_name.replace("?", "")
                if " " in glacier_name:
                    glacier_name = glacier_name.replace(" ", "")
                if "/" in glacier_name:
                    glacier_name = glacier_name.replace("/", "")

                print(glacier_name)

                # skip glacier if area smaller than 11 km2 (but append to results)
                #if glacier_outline.geometry.area.iloc[0] / 1e6 < 15:
                #    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name, glacier_outline.iloc[0]["geometry"])
                #    print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, "!!! area too small")
                #    continue

                # compute bounds of glacier outline
                glacier_extent = dict(zip(['left', 'bottom', 'right', 'top'], glacier_outline.total_bounds))

                # create directory for saving figures for each glacier separately
                if not os.path.isdir(f"figures/{glacier_id}"):
                    os.mkdir(f"figures/{glacier_id}")
                if not os.path.isdir(f"figures/{glacier_id}/{glacier_inventory}"):
                    os.mkdir(f"figures/{glacier_id}/{glacier_inventory}")

                # subset data to glacier outline
                icesat_subset_path = Path(f"cache/{icesat_product}_{glacier_id}_{glacier_inventory}_{year}dh.nc")
                icesatsubsetpath = icesat.icesatSpatialSubset(input_path=data_year_path,
                                           spatial_extent=glacier_extent,
                                           glacier_outline=glacier_outline,
                                           output_path=icesat_subset_path)

                if icesatsubsetpath == 'empty':
                    errormessage = 'subset is empty'
                    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name,
                                        glacier_outline.iloc[0]["geometry"], errormessage)
                    print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, errormessage)
                    continue

                # icesat and dem difference
                #output_path = Path(f'cache/{icesat_product}_{glacier_id}_{year}_dh.nc')
                #icesat_dh_path = analysis.icesatDEMDifference(icesat_subset_path, dem_subset_path, output_path)

                #subset = xr.open_dataset(icesat_dh_path)
                #subset = xr.open_dataset(icesatsubsetpath)
                subset = xr.open_dataset(icesat_subset_path)
                subset = subset.dropna('index')

                icesat_dh_path = icesat_subset_path
                plt.subplots(1, 2)
                plt.title(f'{glacier_name}')
                plt.subplot(1, 2, 1)
                plt.scatter(subset.easting, subset.northing, c=subset.dh)
                import shapely
                polygon = shapely.wkt.loads(str(glacier_outline.iloc[0]["geometry"]))
                plt.plot(*polygon.exterior.xy)
                plt.subplot(1, 2, 2)
                plt.scatter(subset.h, subset.dh, s=2, marker='.', c='orange')
                plt.gca().invert_xaxis()
                plt.show()

                # append path to subset (for future plotting)
                results["dh_path"].loc[{"year": year, "glacier_id": glacier_id}] = str(icesat_dh_path)

                # if the dataset is empty then don't run the analysis
                if type(subset) == str:
                    # append information about empty subset to results and skip running the analysis
                    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name, glacier_outline.iloc[0]["geometry"])
                    print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, "!!!dataset empty")
                    continue

                # drop nan values
                subset = subset.dropna('index')

                if len(subset.index.values) < 7:
                    # append information about empty subset to results and skip running the analysis
                    errormessage = 'less than 7 data points'
                    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name,
                                        glacier_outline.iloc[0]["geometry"], errormessage)
                    print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, "!!!dataset empty")
                    continue


                # create subset only containing lower part
                lower_part = subset.where(subset.h < (max(subset.h)+min(subset.h))/2).dropna('index')

                # count max dh in lower part of glacier
                max_dh = np.percentile(lower_part.dh.values, 90)

                # assign max dh to results
                results["max_dh"].loc[{"year": year, "glacier_id": glacier_id}] = max_dh

                #lower_part = subset.where(subset.h < 400, drop=True)
                #if lower_part.index.size < 5:
                #    results["max_dh"].loc[{"year": year, "glacier_id": glacier_id}] = np.nan
                #else:
                #    max_dh = np.percentile(lower_part.dh.values, 90)
                #    results["max_dh"].loc[{"year": year, "glacier_id": glacier_id}] = max_dh

                #plotting.plotYearlyDH(
                #    icesat_data=subset, glacier_outline=glacier_outline, glacier_name=glacier_name, glacier_id=glacier_id,
                #    output_path=Path(
                #        f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_yearlydh_{glacier_inventory}_{icesat_product}.png')
                #)

                # hypsometric binning of glacier
                try:
                    hypso = analysis.icesatHypso(
                        icesat_data=subset,
                        bins=bins,
                    )
                except:
                    errormessage = 'hypso failed'
                    icesat.fillWithNans(results, year, glacier_id, bins, glacier_name, glacier_outline.iloc[0]["geometry"], errormessage)
                    print(glacier_name, glacier_id, f'{n}/{gl_sum}', year, errormessage)
                    continue

                bin_max = max(hypso["value"][4:])
                results["bin_max"].loc[{"year": year, "glacier_id": glacier_id}] = bin_max

                # do linear regression
                slope, intercept = analysis.linRegHypso(subset.h, subset.dh)

                slope_lower, intercept_lower = analysis.linRegHypso(lower_part.h, lower_part.dh)

                # do linear regression on binned data
                bins_mid = [50, 150, 250, 350, 450, 550, 650, 750, 850, 950, 1050]
                bins_array = np.asarray(bins_mid)
                mask = ~np.isnan(bins_array) & ~np.isnan(hypso['value'].values)
                slope_binned, intercept_binned = analysis.linRegHypso(bins_array, hypso['value'].values)

                # append values to results
                results["slope"].loc[{"year": year, "glacier_id": glacier_id}] = slope
                results["slope_binned"].loc[{"year": year, "glacier_id": glacier_id}] = slope_binned
                results["slope_lower"].loc[{"year": year, "glacier_id": glacier_id}] = slope_lower
                #results["intercept"].loc[{"year": year, "glacier_id": glacier_id}] = intercept
                results["geom"].loc[{"glacier_id": glacier_id}] = glacier_outline.iloc[0]["geometry"]
                results["name"].loc[{"glacier_id": glacier_id}] = glacier_name
                results["surging_rf"].loc[{"year": year, "glacier_id": glacier_id}] = np.nan
                results["surging_threshold"].loc[{"year": year, "glacier_id": glacier_id}] = np.nan

                # todo compute the yearly change (not accumulated change since 2010)

                print(glacier_name, glacier_id, f'{n}/{gl_sum}', year)
            #plt.show()

        # change surge values to True for known surges
        #results = analysis.fillKnownSurges(results)

        # convert xarray dataset to pandas dataframe
        df = results[["glacier_id", "dh_path", "name", "slope", "slope_lower", "slope_binned" , "intercept", "max_dh", "bin_max", "surging_rf", "surging_threshold", "geom"]].to_dataframe().reset_index()
        resultspath = f'cache/results{area}{icesat_product}{glacier_inventory}.csv'
        df.to_csv(resultspath)

    # load cached data
    resultspath = f'cache/results{area}{icesat_product}{glacier_inventory}.csv'
    df = pd.read_csv(resultspath)

    # do threshold analysis
    if False:
        threshold_results = analysis.thresholdAnalysis(df)
        df['surging_threshold'] = threshold_results['surging_threshold']

    # Classify using Random Forest
    rf_resultspath = Path('data/df_results_surging.csv')
    if True:
        # create training dataset
        inputtrainingdatapath = Path('data/trainingdataerik.csv')
        trainingdatapath = analysis.createTrainingDataset(df, inputtrainingdatapath, Path('data/trainingdataerik2.csv'))

        # Random Forest Classification
        rf_results = analysis.classifyRF(df, trainingdatapath)
        df['surging_rf'] = rf_results['surging_rf']

        # save results as csv
        df.to_csv(rf_resultspath)

    df = pd.read_csv(rf_resultspath)

    for index, row in df.iterrows():
        if row['surging_rf'] == 1:
            print(row['name'], row['year'], row['slope'], row['max_dh'])

    plotting.mapSurgesRF(df)

    # PLOT RESULTS
    for glacier_id in glacier_ids:
        # select rows for current glacier id
        glacier = df.where(df['glacier_id'] == glacier_id).dropna(subset=['glacier_id'])

        # create figure
        from matplotlib import pyplot as plt
        plt.close('all')
        plt.subplots(2, 3)
        plt.suptitle(glacier.name.iloc[0])

        # create subplots for each year
        i = 1
        for index, row in glacier.iterrows():
            ax = plt.subplot(2, 3, i)
            try:
                plt.title(f'{row.year}, {row.surging_rf}')
            except:
                plt.title(f'{row.year.iloc[0]}, {max(row.surging_rf.values)}')
            # try if dataset for given year exists, otherwise skip and continue
            try:
                data = xr.open_dataset(row.dh_path)
            except:
                i = i + 1  # increment
                continue

            # plot the elevation pts
            plt.scatter(data['h'], data['dh'], marker='.', s=2, c='orange')
            plt.xlim(0,1200)
            plt.ylim(-60,60)
            ax.invert_xaxis()

            i  = i + 1

        plt.show()













    # -------------------------------------------------------------
    # VALIDATION OF RESULTS
    # with arcticdem
    # -------------------------------------------------------------

    for glacier_id in glacier_ids:
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
