import os
from pathlib import Path
import socket

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

def main():

    # CHOOSE VARIABLES
    # for datasets we want to be working with
    # ---------------------------------------

    # ICESat-2 download specifications
    icesat_product = 'ATL03' # or ATL06 or ATL03
    spatial_extent = [5, 75, 40, 82] # svalbard
    date_range = ['2022-06-01', '2022-07-01']
    icesat_filepath = Path(f'data/icesat_{icesat_product}.nc')

    # Glacier Outlines
    glacier_inventory = 'rgi' # or 'gao'. will assign download url and filenames accordingly

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
    icesat.read_icesat(icesat_product, icesat_filepath)

    # BUILD DEM MOSAIC from NPI (function from Erik)
    dem_mosaic_path = build_dem.build_npi_mosaic(verbose=True)

    # DOWNLOAD GLACIER INVENTORY (RGI or GAO)
    # variables for chosen inventory
    if glacier_inventory == 'rgi':
        glacinv_url = 'https://api.npolar.no/dataset/f6afca5c-6c95-4345-9e52-cfe2f24c7078/_file/3df9512e5a73841b1a23c38cf4e815e3'
        glacinv_filepath = Path('data/rgi.zip')
    if glacier_inventory == 'gao':
        glacinv_url = 'https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v7/regional_files/RGI2000-v7.0-G/RGI2000-v7.0-G-07_svalbard_jan_mayen.zip'
        glacinv_filepath = Path('data/gao.zip')

    # download glacier inventory, function from Erik
    download.download_file(
        url=glacinv_url,
        filename=glacinv_filepath.name,
        directory=glacinv_filepath.parent
    )

    # list of glacier IDs based on selected inventory
    if glacier_inventory == 'gao':
        glacier_ids = [
            13410,
            13218.1,
            13406.1
        ]
    if glacier_inventory == 'rgi':
        glacier_ids = [
            'G016964E77694N',
            'G017525E77773N',
            'G017911E77804N',
            'G016885E77574N'
        ]

    # determine name of ID attribute based on chosen glacier inventory
    if glacier_inventory == 'rgi':
        id_attr = 'glims_id'
    if glacier_inventory == 'gao':
        id_attr = 'IDENT'

    # --------------------------------------------------------------------
    # START OF ACTUAL CODE
    # --------------------------------------------------------------------

    for glacier_id in glacier_ids:

        # load glacier outline
        # todo: cache glacier outline
        glacier_outline = shp.load_shp(
            file_path=str(glacinv_filepath),
            id_attribute_name=id_attr,
            glacier_id=glacier_id)

        glacier_name = glacier_outline.glac_name.iloc[0]

        # create directory for saving figures for each glacier separately
        if not os.path.isdir(f"figures/{glacier_name}/{glacier_inventory}"):
            os.mkdir(f"figures/{glacier_name}/{glacier_inventory}")

        # compute bounds of glacier outline
        spatial_extent = dict(zip(['left', 'bottom', 'right', 'top'], glacier_outline.total_bounds))

        # subset data to glacier outline
        icesat_subset_path = icesat.subset_icesat(
            input_path=icesat_filepath,
            spatial_extent=spatial_extent,
            glacier_outline=glacier_outline,
            output_path=Path(f"cache/{glacier_name}-clipped_{icesat_product}_{glacier_inventory}.nc")) # Scheelebreen-clipped_ATL08_RGI.nc

        dem_subset_path = dems.load_dem(
            input_path=dem_mosaic_path[0],
            spatial_extent=spatial_extent,
            label=f'{glacier_name}_{glacier_inventory}')  # Scheelebreen_RGI

        dem_masked_path= dems.mask_dem(
            dem_subset_path,
            glacier_outline,
            label=f'{glacier_name}_{glacier_inventory}')

        # get elevation difference between ICESat-2 and reference DEM
        icesat_dh_path = analysis.icesat_DEM_difference(
            dem_path=dem_subset_path,
            icesat_path=icesat_subset_path,
            glacier_outline=glacier_outline,
            output_path=Path(f"cache/{glacier_name}-dh-{icesat_product}-{glacier_inventory}.nc")
        )

        bins = analysis.create_bins(icesat_dh_path)

        # hypsometric binning of glacier
        icesat_hypso = analysis.hypso_is2(
            input_path=icesat_dh_path,
            bins=bins
        )

        # plot hypsometric curves and yearly dh for glacier
        plotting.plot_hypso_is2(
            data=icesat_hypso,
            glacier_id=glacier_id,
            glacier_name=glacier_name,
            glacier_area=glacier_outline.geometry.area.iloc[0]/1e6,
            output_path=Path(f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_hypso_{glacier_inventory}-{icesat_product}.png')
        )

        plotting.plot_yearly_dh(
            data_path=icesat_dh_path,
            glacier_outline=glacier_outline,
            glacier_name=glacier_name,
            glacier_id=glacier_id,
            output_path=Path(f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_yearlydh_{glacier_inventory}_{icesat_product}.png')
        )

        print(f'{glacier_name} analysis without errors.')

        break

        # -------------------------------------------------------------
        # VALIDATION OF RESULTS
        # with arcticdem
        # -------------------------------------------------------------

        # path to ArcticDEM directory
        arcticDEM_dir = Path('arcticdem/')
        arcticDEMs = {}

        # subset ArcticDEM rasters to glacier boundary
        for file in os.listdir(arcticDEM_dir):
            year = os.path.split(file)[1][-8:-4]

            arcticDEM_subset_path = dems.load_dem(
                input_path=arcticDEM_dir/file,
                spatial_extent=spatial_extent,
                label=f'arcticdem_{glacier_name}_{glacier_inventory}_{year}')

            arcticDEM_masked_path = dems.mask_dem(
                dem_path=arcticDEM_subset_path,
                glacier_outline=glacier_outline,
                label=f'arcticdem_{glacier_name}_{glacier_inventory}_{year}')

            arcticDEMs[year] = arcticDEM_masked_path

        # hypsometric bins
        arcticDEM_hypso = analysis.hypso_dem(
            dems=arcticDEMs,
            bins=bins,
            ref_dem=dem_masked_path
        )

        print(f'{glacier_name} validation without errors.')

        # plot hypso curves
        plotting.plot_hypso_arcticdem(
            data=arcticDEM_hypso,
            glacier_id=glacier_id,
            glacier_name=glacier_name,
            glacier_area=glacier_outline.area.iloc[0]/1e6,
            output_path=Path(f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_ademhypso_{glacier_inventory}.png')
        )

        # plot elevation differences
        for year in arcticDEMs:
            if year != '2022':
                plotting.plot_arcticDEM_dh(
                    data=arcticDEMs,
                    ref_dem_path=dem_masked_path,
                    year=year,
                    glacier_outline=glacier_outline,
                    glacier_name=glacier_name,
                    glacier_id=glacier_id,
                    output_path=Path(f'figures/{glacier_name}/{glacier_inventory}/{glacier_id}_ademhypso{year}_{glacier_inventory}.png'),
                )

if __name__ == "__main__":
    main()
