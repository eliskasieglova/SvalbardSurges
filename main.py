import xarray as xr
import socket
import os
from pathlib import Path

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

from svalbardsurges import plotting
from svalbardsurges import analysis
from svalbardsurges import utilities
from svalbardsurges import download
from svalbardsurges import paths
from svalbardsurges import build_dem
from svalbardsurges.inputs import dems
from svalbardsurges.inputs import shp
from svalbardsurges.inputs import is2

def main():

    # create directories for caching and saving figures if do not exist
    if not os.path.isdir("cache/"):
        os.mkdir("cache/")

    if not os.path.isdir("figures/"):
        os.mkdir("figures/")

    # build DEM mosaic
    dem_mosaic_path = build_dem.build_npi_mosaic(verbose=True) #DEM (NPI)

    # download Glacier Area Outlines
    if not paths.gao_path.is_file():
        download.download_file(paths.gao_url, paths.gao_path)

    # list of glacier IDs
    glacier_ids = [13406.1,
                   13218.1,
                   13499.02,
                   13410,
                   13218.2,
                   13408.1,
                   13412,
                   13413.1,
                ]

    #
    for glacier_id in glacier_ids:
        # load glacier outline
        glacier_outline = shp.load_shp(paths.gao_path, glacier_id)
        glacier_name = glacier_outline.NAME.iloc[0]

        # create directory for saving figures
        if not os.path.isdir(f"figures/{glacier_name}"):
            os.mkdir(f"figures/{glacier_name}")

        # compute bounds of glacier outline
        bounds = dict(zip(['left', 'bottom', 'right', 'top'], glacier_outline.total_bounds))

        # subset data to glacier outline
        is2_subset_path = is2.subset_is2(
            input_path=paths.is2_path,
            bounds=bounds,
            glacier_outline=glacier_outline,
            output_path=Path(f"cache/{glacier_name}-is2-clipped.nc"))

        dem_subset_path = dems.load_dem(
            input_path=dem_mosaic_path,
            bounds=bounds,
            label=glacier_name)

        # get elevation difference between IS2 and reference DEM
        is2_dh_path = analysis.IS2_DEM_difference(
            dem_path=dem_subset_path,
            is2_path=is2_subset_path,
            glacier_outline=glacier_outline,
            output_path=Path(f"cache/{glacier_name}-is2-dh.nc"))

        # hypsometric binning of glacier
        hypso = analysis.hypsometric_binning(is2_dh_path)

        # plot hypsometric curves and yearly dh for glacier
        plotting.plot_hypso_curves(
            data=hypso,
            glacier_id=glacier_id,
            glacier_name=glacier_name,
            glacier_area=glacier_outline.geometry.area.iloc[0]/1e6,
            output_path=Path(f'figures/{glacier_name}/{glacier_id}_hypsocurves.png'))

        plotting.plot_yearly_dh(
            data_path=is2_dh_path,
            glacier_outline=glacier_outline,
            glacier_name=glacier_name,
            glacier_id=glacier_id,
            output_path=Path(f'figures/{glacier_id}_yearlydh.png'))

        # validate results using ArcticDEM
        #svalbardsurges.inputs.dems.validate(Path('arcticdem/'),
        #                                    subset_dem,
        #                                    bounds,
        #                                    glacier_outline,
        #                                    Path('arcticdem_year'))

        print(f'Glacier {glacier_id} without errors.')

if __name__ == "__main__":
    main()
