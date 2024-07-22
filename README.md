# SvalbardSurges

An innovative methodology on glacier surge detection with ICESat-2 data in Svalbard. This project was created as part of my diploma thesis at the Charles University in Prague in collaboration with the University in Oslo.

Glacier surges are characterized by rapid accelerations in glacier flow followed by periods of quiescence and are significant in understanding glacier dynamics and their broader environmental implications. While stable glaciers are gaining mass in the accumulation zone and losing mass in the ablation zone (Hornbreen), surging glaciers show large positive elevation changes near the terminus and mass loss in the upper parts of the glacier (Monacobreen). This difference in elevation changes is the main presumption that detecting surges using elevation changes from ICESat-2 should work. This project preprocesses ICESat-2 data uses a reference DEM for measuring elevation changes and employs a random forest algorithm, along with innovative filtering techniques, to identify surging activity.

![image](https://github.com/user-attachments/assets/30a6b33d-6cda-4ecf-98b1-d8c118713634)
![image](https://github.com/user-attachments/assets/9cb51aea-4e56-4b6f-a676-456e3e345329)

The results were validated against known surging glaciers and compared with SAR-derived velocity changes from Koch et al. (2023). The methodology successfully detected nearly all surges identified by Koch et al. (2023) and identified additional surges, including the newest one on Borebreen. However, it also detected more instabilities than actual surges, highlighting areas of potential instability. The method's limitations include noise in cloudy years, dependency on a reference DEM – complicating its application outside Svalbard – and a limited amount of training data. Despite these challenges, the approach demonstrates the potential of using elevation data alone for surge detection. Future research should aim to expand beyond Svalbard to enhance the method's accuracy.

## Installation and How To Run
pyproj seems to sometimes not work properly from the conda-forge channel, and may need to be installed with pip instead.

```bash
conda remove -f pyproj
pip install pyproj
```
For downloading the ICESat-2 data it is necessary to have your EARTHDATA username and password saved as environmental variables EARTHDATA_USERNAME and EARTHDATA_PASSWORD.

See installation requirements for packages in environment.xml.

## User defined variables
There are some user defined variables to be edited before the script is run. 

```
label = 'area'  ## label of the area selected by the user. this will then choose the according spatial extent. values can be 'svalbard' (reccommended), 'heerland', 'heerlandextended' or 'south'
products = ['product']  ## list of ICESat-2 products to be downloaded. the script is intended for either ['ATL06'] (recommended) or ['ATL08'] or ['ATL06', 'ATL08']
date_range = ['start_date', 'end_date']  # list of start date and end date in format YYYY-MM-DD. recommended ['2018-11-01', '2023-10-31'].
```

These variables define the amount and type of data that will be downloaded and used for the classification of surges in Svalbard.


# Documentation

## Structure of files
- main.py: main file to run
- management.py: functions for managing data (creating folders, reading shapefiles, data type conversions)
- preprocessing.py: functions used in preprocessing (filtering, clipping, normalizing)
- analysis.py: functions used in data analysis (binning data, extracting features)
- classify.py: functions for classifications using sklearn (random forest)
- plotting.py: plotting functions, mainly for one time usage
- glacier_names.py: dictionary of glacier names to be retrieved based on glacier ID
- user_vars.py: user variables to be defined by user

In the main file, first, directories needed for this project are created.

```
# create the necessary directories
management.createDirs()
```

![image](https://github.com/user-attachments/assets/acce4c53-b5a6-49db-9822-5627e0f47cb5)

Then, the function for downloading the ICESat-2 data is called. The download is done using the icepyx package and unfortunately the download using icepyx often crashes due to timeout of request. The solution is to either keep trying until the download is successful, or make the amount of data for download smaller - for example download each year separately. This function downloads the data based on the input settings - label, products and date_range.



## Notes


## Detailed project description


## Credits
This project was developed in collaboration with people at the University in Oslo, namely Erik Schytt Mannerfelt and Désirée Treichler.
