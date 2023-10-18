from pathlib import Path

# auxiliary file for storing paths

# download URLs
dem_url = 'https://public.data.npolar.no/kartdata/S0_Terrengmodell/Delmodell/NP_S0_DTM5_2011_25163_33.zip'
gao_url = 'https://api.npolar.no/dataset/f6afca5c-6c95-4345-9e52-cfe2f24c7078/_file/3df9512e5a73841b1a23c38cf4e815e3'
rgi_url = 'https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v7/regional_files/RGI2000-v7.0-C/RGI2000-v7.0-C-07_svalbard_jan_mayen.zip'

# paths
is2_path = Path('nordenskiold_land-is2.nc')
dem_filename = Path('NP_DEMs/NP_S0_DTM5_2011_25163_33/S0_DTM5_2011_25163_33.tif')
gao_path = Path('gao.zip')



