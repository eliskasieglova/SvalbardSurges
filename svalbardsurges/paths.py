from pathlib import Path

# auxiliary file for storing paths

# download URLs
dem_url = 'https://public.data.npolar.no/kartdata/S0_Terrengmodell/Delmodell/NP_S0_DTM5_2011_25163_33.zip'
gao_url = 'https://api.npolar.no/dataset/f6afca5c-6c95-4345-9e52-cfe2f24c7078/_file/3df9512e5a73841b1a23c38cf4e815e3'
rgi_url = 'https://daacdata.apps.nsidc.org/pub/DATASETS/nsidc0770_rgi_v7/regional_files/RGI2000-v7.0-G/RGI2000-v7.0-G-07_svalbard_jan_mayen.zip'

# file names
is2_name = 'nordenskiold_land-is2.nc'
dem_name = 'NP_DEMs/NP_S0_DTM5_2011_25163_33/S0_DTM5_2011_25163_33.tif'
gao_name = 'gao.zip'
rgi_name = 'rgi.zip'

# paths
is2_path = Path(f'{is2_name}')
dem_path = Path(f'{dem_name}')
gao_path = Path(f'cache/{gao_name}')
rgi_path = Path(f'cache/{rgi_name}')




