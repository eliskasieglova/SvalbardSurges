import xarray as xr
import socket
import os

# The PROJ installation points to the wrong directory for the proj.db file, which needs to be fixed on this computer
if socket.gethostname() == "DESKTOP-09DFBN6":
    os.environ["PROJ_DATA"] =  "C:\\Users\\eliss\\anaconda3\\envs\\SvalbardSurges\\Lib\\site-packages\\pyproj\\proj_dir\\share\\proj"

import svalbardsurges.plotting
import svalbardsurges.analysis
import svalbardsurges.utilities
import svalbardsurges.inputs.is2
import svalbardsurges.inputs.dems
import svalbardsurges.inputs.shp
import svalbardsurges.download_file
import svalbardsurges.paths
import svalbardsurges.build_dem

def main():

    # open IS2 data
    is2 = xr.open_dataset(svalbardsurges.paths.is2_filename)

    # download DEM and glacier area outlines
    dem = svalbardsurges.download_file.download_file(svalbardsurges.paths.dem_url, 'dem.zip')
    gao = svalbardsurges.download_file.download_file(svalbardsurges.paths.gao_url, 'gao.zip')

    # list of glacier ids
    glacier_ids = [13218.1,
                   13406.1,
                   13499.02,
                   13410,
                   13413.1,
                   13218.2,
                   13408.1,
                   13412
                ]

    for glacier_id in glacier_ids:

        label = str(glacier_id)

        # load single glacier outline based on glacier ID
        glacier_outline = svalbardsurges.inputs.shp.load_shp(glacier_id)

        # set bounds according to glacier outline
        bounds = dict(zip(['left', 'bottom', 'right', 'top'], glacier_outline.total_bounds))
        svalbardsurges.build_dem.build_npi_mosaic(verbose=True)

        # subset DEM and IS2 data by chosen bounds
        #dem_subset_path = svalbardsurges.inputs.dems.load_dem(bounds, label)
        is2_subset = svalbardsurges.analysis.subset_is2(is2, bounds, label)

        # clip DEM to glacier area outline
        masked_dem = svalbardsurges.inputs.dems.mask_dem('cache/npi_vrts/npi_mosaic.vrt', glacier_outline, label)

        # get elevation difference between IS2 and reference DEM
        is2_dh = svalbardsurges.analysis.IS2_DEM_difference(masked_dem, is2_subset, label)

        # do hypsometric binning of glacier
        #hypso = svalbardsurges.analysis.hypsometric_binning(is2_dh)

        # compute statistics
        #stat = svalbardsurges.analysis.statistics(is2_dh)

        # plot hypsometric curves
        svalbardsurges.plotting.plot_hypso_curves(is2_dh, label, glacier_outline)
        svalbardsurges.plotting.plot_yearly_dh(is2_dh, label, glacier_outline)


        print(f'Glacier {label} without errors.')

if __name__ == "__main__":
    main()
