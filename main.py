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

def main():

    # open IS2 data
    data = xr.open_dataset("nordenskiold_land-is2.nc")

    # set bounds for subsetting data
    bounds = {
        "bottom": 8617861,
        "right": 552643,
        "top": 8637186,
        "left": 540154
    }

    # subset IS2 data by bounds
    is2_subset = svalbardsurges.analysis.subset_is2(data, bounds, "scheelebreen")

    # load DEM cropped to bounds
    dem_subset = svalbardsurges.inputs.dems.load_dem(bounds, "scheelebreen")

    # load shapefile
    scheelebreen_shp = svalbardsurges.inputs.shp.load_shp(13406.1)

    # clip DEM to glacier area outlines
    masked_dem = svalbardsurges.inputs.dems.mask_dem(dem_subset, scheelebreen_shp)

    # get elevation difference between IS2 and reference DEM
    is2_dh = svalbardsurges.analysis.IS2_DEM_difference(masked_dem, is2_subset, "scheelebreen")

    # hypsometric binning
    hypso = svalbardsurges.analysis.hypsometric_binning(is2_dh)

    # plot hypsometric curves
    svalbardsurges.plotting.plot_hypso_curves(hypso)

if __name__ == "__main__":
    main()
