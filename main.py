import os
from pathlib import Path
import socket
import pandas as pd

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

from svalbardsurges import plotting
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
    icesat_product = 'ATL08'  # or ATL06 or ATL03
    date_range = ['2018-10-14', '2023-11-10']
    icesat_filepath = Path(f'data/icesat_{icesat_product}.nc')
    glacier_inventory = 'rgi' # 'rgi' or 'gao'. will assign download url and filenames accordingly
    area = "heer land"

    hypso_threshold = 10
    ransac_threshold = 0.5

    bboxes = {"svalbard": [5, 75, 40, 82], "heer land": [15.7, 77.35, 18.6, 78]}
    spatial_extent = bboxes[area]

    # ------------------------------------------------------------------------
    # CHOOSE ALGORITHMS
    # choose which parts of code will be run and which not (True = will be run, False = will not be run)
    # ------------------------------------------------------------------------

    hypso = True # hypsometric binning
    ransac = True # RANSAC analysis
    linearregression = True
    validate = False # validation of dh from icesat compared to arcticdem

    pltshow = True # plotting of results
    pltsave = False

    testdata = True
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
    dem_mosaic_path = build_dem.build_npi_mosaic(verbose=True)

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

    # list of glacier IDs based on selected inventory
    # todo test the results on these two glacier inventories (on the same glaciers)
    if glacier_inventory == 'gao':
        glacier_ids = [
            #12412,      # Storbreen
            13406.1,    # Scheelebreen
            13218.1,    # Doktorbreen
            #17310.1,    # Hinlopenbreen
            #15511.1     # Kongsbreen
        ]

    if glacier_inventory == 'rgi':
        glacier_ids = [
            'G016964E77694N',   # Scheelebreen
            #'G017525E77773N',
            #'G017911E77804N',
            #'G016885E77574N',
            #'G016172E77192N'  # Storbreen
        ]

    # determine name of ID attribute based on chosen glacier inventory
    if glacier_inventory == 'rgi':
        id_attr = 'glims_id'
    if glacier_inventory == 'gao':
        id_attr = 'IDENT'

    # loop through all the glaciers in dataset
    #glacier_ids = shp.getIDs(glacinv_filepath, id_attr)

    # select glaciers inside bounding box (spatial extent)
    #glaciers = shp.withinBBox(spatial_extent, glacinv_filepath, Path(f'cache/{area}.shp'))
    #glacier_ids = shp.getIDs(Path(f'cache/{area}.shp'), id_attr)

    # empty pd dataframe where the results of the analyses will go
    results = pd.DataFrame(
        index=glacier_ids,
        columns=[
            "glacier_name",
            "surge",
            "surgevalues",
            "geom",
            "icesat_path",
            "dem_path",
            "latlon",
            "data_exists"
        ]
    )

    surgenosurge = pd.DataFrame(
        index=['hypso', 'ransac', 'linreg', 'sum'],
        columns=[2018, 2019, 2020, 2021, 2022]
    )

    surgevalues = pd.DataFrame(
        index=['hypso', 'ransac', 'linreg'],
        columns=[2018, 2019, 2020, 2021, 2022]
    )

    # --------------------------------------------------------------------
    # START OF ACTUAL CODE
    # --------------------------------------------------------------------
    # loop through all the glaciers

    gl_sum = len(glacier_ids)
    i = 0
    for glacier_id in glacier_ids:
        i = i + 1
        # load glacier outline
        glacier_outline = shp.load_shp(
            file_path=str(glacinv_filepath),
            id_attribute_name=id_attr,
            glacier_id=glacier_id)

        # compute bounds of glacieroutline
        spatial_extent = dict(zip(['left', 'bottom', 'right', 'top'], glacier_outline.total_bounds))

        # determine NAME column in attribute table
        if glacier_inventory == 'rgi':
            glacier_name = glacier_outline.glac_name.iloc[0]
        elif glacier_inventory == 'gao':
            glacier_name = glacier_outline.NAME.iloc[0]

        # if the glacier name is None it means it's meaningles heheh (or like too small to surge, maybe)?
        # todo if glacier area smaller than something then skip it
        if (glacier_name == None) | (glacier_name == 'NEW0159'):
            continue

        # if there is a symbol that's causing troubles
        if "?" in glacier_name:
            glacier_name = glacier_name.replace("?", "")
        if " " in glacier_name:
            glacier_name = glacier_name.replace(" ", "")
            glacier_name = glacier_name.replace("/", "")

        # add record of glacier name, geometry to pd dataframe
        results['glacier_name'][glacier_id] = glacier_name
        results['geom'][glacier_id] = glacier_outline.geometry.iloc[0]
        print(glacier_name, glacier_id)

        # create directory for saving figures for each glacier separately
        if not os.path.isdir(f"figures/{glacier_id}"):
            os.mkdir(f"figures/{glacier_id}")
        if not os.path.isdir(f"figures/{glacier_id}/{glacier_inventory}"):
            os.mkdir(f"figures/{glacier_id}/{glacier_inventory}")

        # subset data to glacier outline
        icesat_subset_path = icesat.icesatSpatialSubset(
            input_path=icesat_filepath,
            spatial_extent=spatial_extent,
            glacier_outline=glacier_outline,
            output_path=Path(f"cache/{glacier_name}-clipped_{icesat_product}_{glacier_inventory}.nc")) # Scheelebreen-clipped_ATL08_RGI.nc

        # if the dataset is empty then don't run the analysiss
        # todo exceptions
        if icesat_subset_path == 'empty':
            # append information about empty subset to results and skip running the analysis
            results['data_exists'][glacier_id] = False
            continue
        else:
            # if data exists just append the information about that to the df
            results['data_exists'][glacier_id] = True

        dem_subset_path = dems.load_dem(
            input_path=dem_mosaic_path[0],
            spatial_extent=spatial_extent,
            label=f'{glacier_name}_{glacier_inventory}')  # Scheelebreen_RGI

        dem_masked_path= dems.mask_dem(
            dem_subset_path,
            glacier_outline,
            label=f'{glacier_name}_{glacier_inventory}',
            pltshow=pltshow
            )

        # get elevation difference between ICESat-2 and reference DEM
        icesat_dh_path = analysis.icesat_DEM_difference(
            dem_path=dem_subset_path,
            icesat_path=icesat_subset_path,
            glacier_outline=glacier_outline,
            output_path=Path(f"cache/{glacier_name}-dh-{icesat_product}-{glacier_inventory}.nc")
        )

        if icesat_dh_path == 'empty':
            results['data_exists'][glacier_id] = False
            continue

        # append path to subsetted icesat-2 to dictionary
        results['icesat_path'][glacier_id] = icesat_dh_path

        plotting.plot_yearly_dh(
            data_path=icesat_dh_path, glacier_outline=glacier_outline, glacier_name=glacier_name, glacier_id=glacier_id,
            output_path=Path(f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_yearlydh_{glacier_inventory}_{icesat_product}.png'),
            pltshow=pltshow, pltsave=pltsave
        )

        # ANALYSIS
        if hypso:
            # hypsometric binning of glacier
            # todo remove threshold part (this will be in evaluate hypso)
            bins = analysis.create_bins(icesat_dh_path)
            hypso, surgenosurge, surgevalues = analysis.icesatHypso(
                input_path=icesat_dh_path,
                bins=bins,
                surgenosurge = surgenosurge,
                surgevalues=surgevalues,
                threshold=hypso_threshold
            )

            # surge or not surge?
            # todo remove this part from the function above
            analysis.evaluateHypso(hypso)

            # plot hypsometric curves and yearly dh for glacier
            plotting.plotHypso(
                data=hypso,
                glacier_id=glacier_id,
                glacier_name=glacier_name,
                glacier_area=glacier_outline.geometry.area.iloc[0]/1e6,
                output_path=Path(f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_hypso_{glacier_inventory}-{icesat_product}.png'),
                pltshow=pltshow,
                pltsave=pltsave
            )

            # todo plot hypso with the linear regression

        if ransac:
            surgenosurge, surgevalues = analysis.regression("ransac", icesat_dh_path, surgenosurge, surgevalues, ransac_threshold,
                                                        glacier_name, pltshow, pltsave)

        if linearregression:
            surgenosurge, surgevalues = analysis.regression("linreg", icesat_dh_path, surgenosurge, surgevalues, ransac_threshold,
                                                        glacier_name, pltshow, pltsave)

        # update sums in surgenosurge df
        surgenosurge = analysis.updateSurgeSum(surgenosurge)

        # append surges to results df
        results.loc[glacier_id, 'surge'] = list(surgenosurge.iloc[-1])
        results.loc[glacier_id, 'surgevalues'] = (surgevalues.iloc[0], surgevalues.iloc[1])

        # todo write df in file

        print(surgenosurge)
        print(surgevalues)
        print(f'{glacier_name} analysis done.')
        print(f'{i}/{gl_sum} done')

    plotting.plotSurges('none', results, pltshow, pltsave)

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
                    input_path=arcticdem_dir/file,
                    spatial_extent=spatial_extent,
                    label=f'arcticdem_{glacier_name}_{glacier_inventory}_{year}')

                arcticdem_masked_path = dems.mask_dem(
                    dem_path=arcticdem_subset_path,
                    glacier_outline=glacier_outline,
                    label=f'arcticdem_{glacier_name}_{glacier_inventory}_{year}',
                    pltshow=pltshow)

                arcticdems[year] = arcticdem_masked_path

            # hypsometric bins
            arcticdem_hypso = analysis.hypso_dem(
                dems=arcticdems,
                bins=bins,
                ref_dem=dem_masked_path
            )

            print(f'{glacier_name} validation without errors.')

            # plot hypso curves
            plotting.plot_hypso_arcticdem(
                data=arcticdem_hypso,
                glacier_id=glacier_id,
                glacier_name=glacier_name,
                glacier_area=glacier_outline.area.iloc[0]/1e6,
                output_path=Path(f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_ademhypso_{glacier_inventory}.png'),
                pltshow=pltshow, pltsave=pltsave
            )

            # plot elevation differences
            for year in arcticdems:
                if year != '2022':
                    plotting.plot_arcticDEM_dh(
                        data=arcticdems,
                        ref_dem_path=dem_masked_path,
                        year=year,
                        glacier_outline=glacier_outline,
                        glacier_name=glacier_name,
                        glacier_id=glacier_id,
                        output_path=Path(f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_ademhypso{year}_{glacier_inventory}.png'),
                        pltshow=pltshow, pltsave=pltsave
                    )


if __name__ == "__main__":
    main()