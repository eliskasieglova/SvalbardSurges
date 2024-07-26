from pathlib import Path

import geopandas as gpd
import pandas as pd

import analysis
import classification
import download
import management
import plotting
import preprocessing
import read_icesat
from glacier_names import glacier_names
from user_vars import label, spatial_extent, products

import os
os.chdir('publish/')

# create the necessary directories
management.createDirs()

# download ICESat-2 data based on date range and products (specifications in vars.py)
download.downloadSvalbard()

# read ICESat-2 data
data = read_icesat.readICESat(products)

# count elevation change
dh_path = Path(f'data/{label}_dh.csv')
if not dh_path.is_file():
    # read csv data points as pandas dataframe
    print('reading data')
    data = pd.read_csv(f'data/ICESat.csv')

    # drop points with unknown elevation
    data = data.dropna(subset=['h'])

    # subset ICESat-2 data to bounding box of selected area (if not for whole of svalbard)
    if label != 'svalbard':
        icesat = analysis.subsetICESat(data, spatial_extent)
    else:
        icesat = data

    # count dh
    icesat = preprocessing.dh(icesat)

else:
    icesat = pd.read_csv(dh_path, engine="pyarrow")

# select glaciers from RGI inside the bounding box of selected area
rgi = analysis.selectGlaciersFromRGI(spatial_extent)

# list glacier IDs in the selected area
glacier_ids = management.listGlacierIDs(rgi)
total = len(glacier_ids)

# create glacier subsets
clipping_unsuccessful = []
f = 1
for glacier_id in glacier_ids:
    print(f'{f}/{total} ({glacier_id})')
    f = f+1

    # set output path
    outpath = Path(f'temp/glaciers/{glacier_id}_icesat_clipped.gpkg')

    # cache
    if outpath.is_file():
        continue

    # load glacier shapefile
    try:
        glacier = management.loadGlacierShapefile(glacier_id)
    except:
        print(f'{glacier_id} shp not working')
        continue
    # read glacier name
    try:
        glacier_name = glacier_names[glacier_id]
    except:
        glacier_name = 'nan'

    # clip
    try:
        clipped = preprocessing.clipICESat(icesat, glacier)
        clipped.to_file(outpath)
    except:
        clipping_unsuccessful.append(glacier_id)

# print glaciers where clipping was not successful
print(clipping_unsuccessful)

# filter and normalize
filtering_unsuccessful = []
f = 1
for glacier_id in glacier_ids:
    print(f'{f}/{total} ({glacier_id})')
    f = f+1

    # set output path
    outpath = Path(f'temp/glaciers/{glacier_id}_filtered.gpkg')

    # cache
    if outpath.is_file():
        continue

    # open dataset
    try:
        data = gpd.read_file(f'temp/glaciers/{glacier_id}_icesat_clipped.gpkg')
    except:
        filtering_unsuccessful.append(glacier_id)
        continue

    # filter, normalize, save
    try:
        filtered = preprocessing.filterWithRANSAC(data, glacier_id)
        normalized = preprocessing.normalize(filtered)
        normalized.to_file(outpath)
    except:
        # if the filtering is unsuccessful, print it later (just for information)
        filtering_unsuccessful.append(glacier_id)
        continue

print(f'filtering unsuccessful: {filtering_unsuccessful}')

# group data by hydrological years
print('grouping by hydro years')
#try:
#    print(icesat['acquisition_time'])
#except:
#    icesat['acquisition_time'] = icesat['date']
#icesat['date'] = [str(x) for x in icesat['acquisition_time']]
#icesat['date'] = [x[:10] for x in icesat['date']]

years = [2019, 2020, 2021, 2022, 2023]
i = 0
tot = len(glacier_ids)
for glacier_id in glacier_ids:
    print(f'{i}/{tot} {glacier_id}')
    i = i+1

    #cache
    outpath = Path(f'temp/glaciers/{glacier_id}_filtered.gpkg')
    if outpath.is_file():
        continue

    # open pts for glacier
    try:
        data = gpd.read_file(outpath)
    except:
        continue

    # loop through years and create subset by hydrological year
    for year in years:
        print(year)
        preprocessing.groupByHydroYear(data, year, glacier_id)

# extract the features for individual glaciers
analysis.runFeatureExtraction()

# count yearly changes on the extracted features
analysis.countYearlyChanges()

# classify using Random Forest
classification.classify()

# plot results
plotting.plotResultsMaps()
