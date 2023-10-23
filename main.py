import socket
import os
from pathlib import Path

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

from svalbardsurges import plotting
from svalbardsurges import analysis
from svalbardsurges import download
from svalbardsurges import paths
from svalbardsurges import build_dem
from svalbardsurges.inputs import dems
from svalbardsurges.inputs import shp
from svalbardsurges.inputs import is2

def main():

    dataset = 'rgi'

    # create directories for caching and saving figures if do not exist
    if not os.path.isdir("cache/"):
        os.mkdir("cache/")

    if not os.path.isdir("figures/"):
        os.mkdir("figures/")

    # build DEM mosaic
    dem_mosaic_path = build_dem.build_npi_mosaic(verbose=True)

    # download glacier outlines (RGI or GAO)
    if not paths.rgi_path.is_file():
        download.download_file(paths.rgi_url, paths.rgi_name)

    # list of glacier IDs

    if dataset == 'gao':
        glacier_ids = [
            13410,
            13218.1,
            13406.1
        ]

    if dataset == 'rgi':
        glacier_ids = [
            'G016964E77694N',
            'G017525E77773N',
            'G017911E77804N',
            'G016885E77574N'
        ]

    for glacier_id in glacier_ids:

        # load glacier outline
        glacier_outline = shp.load_shp(
            file_path=str(paths.rgi_path),
            id_attribute_name='glims_id',
            glacier_id=glacier_id)

        glacier_name = glacier_outline.glac_name.iloc[0]

        # create directory for saving figures
        if not os.path.isdir(f"figures/{glacier_name}"):
            os.mkdir(f"figures/{glacier_name}")

        if not os.path.isdir(f"figures/{glacier_name}/{dataset}"):
            os.mkdir(f"figures/{glacier_name}/{dataset}")

        # compute bounds of glacier outline
        bounds = dict(zip(['left', 'bottom', 'right', 'top'], glacier_outline.total_bounds))

        # subset data to glacier outline
        is2_subset_path = is2.subset_is2(
            input_path=paths.is2_path,
            bounds=bounds,
            glacier_outline=glacier_outline,
            output_path=Path(f"cache/{glacier_name}-is2-clipped_{dataset}.nc"))

        dem_subset_path = dems.load_dem(
            input_path=dem_mosaic_path[0],
            bounds=bounds,
            label=f'{glacier_name}_{dataset}')

        dem_masked_path= dems.mask_dem(
            dem_subset_path,
            glacier_outline,
            label=f'{glacier_name}_{dataset}')

        # get elevation difference between IS2 and reference DEM
        is2_dh_path = analysis.IS2_DEM_difference(
            dem_path=dem_subset_path,
            is2_path=is2_subset_path,
            glacier_outline=glacier_outline,
            output_path=Path(f"cache/{glacier_name}-is2-dh_{dataset}.nc")
        )

        bins = analysis.create_bins(is2_dh_path)

        # hypsometric binning of glacier
        is2_hypso = analysis.hypso_is2(
            input_path=is2_dh_path,
            bins=bins
        )

        # plot hypsometric curves and yearly dh for glacier
        plotting.plot_hypso_is2(
            data=is2_hypso,
            glacier_id=glacier_id,
            glacier_name=glacier_name,
            glacier_area=glacier_outline.geometry.area.iloc[0]/1e6,
            output_path=Path(f'figures/{glacier_name}/{dataset}/{glacier_id}_hypso_{dataset}.png')
        )

        plotting.plot_yearly_dh(
            data_path=is2_dh_path,
            glacier_outline=glacier_outline,
            glacier_name=glacier_name,
            glacier_id=glacier_id,
            output_path=Path(f'figures/{glacier_name}/{dataset}/{glacier_id}_yearlydh_{dataset}.png')
        )

        print(f'{glacier_name} analysis without errors.')

        # validate results using ArcticDEM
        # --------------------------------

        # path to ArcticDEM directory
        arcticDEM_dir = Path('arcticdem/')

        arcticDEMs = {}

        # subset ArcticDEM rasters to glacier boundary
        for file in os.listdir(arcticDEM_dir):
            year = os.path.split(file)[1][-8:-4]

            arcticDEM_subset_path = dems.load_dem(
                input_path=arcticDEM_dir/file,
                bounds=bounds,
                label=f'arcticdem_{glacier_name}_{dataset}_{year}')

            arcticDEM_masked_path = dems.mask_dem(
                dem_path=arcticDEM_subset_path,
                glacier_outline=glacier_outline,
                label=f'arcticdem_{glacier_name}_{dataset}_{year}')

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
            output_path=Path(f'figures/{glacier_name}/{dataset}/{glacier_id}_ademhypso_{dataset}.png')
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
                    output_path=Path(f'figures/{glacier_name}/{dataset}/{glacier_id}_ademhypso{year}_{dataset}.png'),
                )

if __name__ == "__main__":
    main()
