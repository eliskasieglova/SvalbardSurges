# SvalbardSurges

I present an innovative method on detecting glacier surges in Svalbard based on elevation changes derived from ICESat-2 data. This project was created as part of my diploma thesis at the Charles University in Prague in collaboration with the University in Oslo.

## Installation
pyproj seems to sometimes not work properly from the conda-forge channel, and may need to be installed with pip instead.

```bash
conda remove -f pyproj
pip install pyproj
```
For downloading the ICESat-2 data it is necessary to have your EARTHDATA username and password saved as environmental variables EARTHDATA_USERNAME and EARTHDATA_PASSWORD.

See installation requirements for packages in environment.xml.

## Structure
- main.py: main file to run
- management.py: functions for managing data (creating folders, reading shapefiles, data type conversions)
- preprocessing.py: functions used in preprocessing (filtering, clipping, normalizing)
- analysis.py: functions used in data analysis (binning data, extracting features)
- classify.py: functions for classifications using sklearn (random forest)
- plotting.py: plotting functions, mainly for one time usage
- glacier_names.py: dictionary of glacier names to be retrieved based on glacier ID
- user_vars.py: user variables to be defined by user

## User defined variables
There are some user defined variables to be edited before the script is run. 

```
label = 'area'  ## label of the area selected by the user. this will then choose the according spatial extent. values can be 'svalbard' (reccommended), 'heerland', 'heerlandextended' or 'south'
products = ['product']  ## list of ICESat-2 products to be downloaded. the script is intended for either ['ATL06'] (recommended) or ['ATL08'] or ['ATL06', 'ATL08']
date_range = ['start_date', 'end_date']  # list of start date and end date in format YYYY-MM-DD. recommended ['2018-11-01', '2023-10-31'].
```

These variables define the amount and type of data that will be downloaded and used for the classification of surges in Svalbard.

## Notes
Download using icepyx often crashes due to timeout of request. The solution is to either keep trying until the download is successful, or make the amount of data for download smaller, for example download each year separately.

## Detailed project description


## Credits
This project was developed in collaboration with people at the University in Oslo, namely Erik Schytt Mannerfelt and Désirée Treichler.
