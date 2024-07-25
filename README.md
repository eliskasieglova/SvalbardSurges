# SvalbardSurges

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

The CRS used is EPSG:32633.

**Data you have to have downloaded before running this script:**
- Randolph Glacier Inventory (https://www.glims.org/RGI/)
- NPI DEMs (https://public.data.npolar.no/kartdata/S0_Terrengmodell/Delmodell/)
- training data (in this Github repository)

## User defined variables
It is necessary to update the user defined variables in the script user_vars.py. Except for the download specifications (below) you have to update your path to where you have the Randolph Glacier Inventory saved.

```
label = 'area'  ## label of the area selected by the user. this will then choose the according spatial extent. values can be 'svalbard' (reccommended), 'heerland', 'heerlandextended' or 'south'
products = ['product1', 'product2']  ## list of ICESat-2 products to be downloaded. the script is intended for either ['ATL06'] (recommended) or ['ATL08'] or ['ATL06', 'ATL08']
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

### 1. Setting up user defined variables

![image](https://github.com/user-attachments/assets/ee4e906e-602b-4390-b79f-48030efd9623)

### 2. Creating directory structure
In the main file, first, directories needed for this project are created.
```
# create the necessary directories
management.createDirs()
```
![image](https://github.com/user-attachments/assets/acce4c53-b5a6-49db-9822-5627e0f47cb5)

### 3. Downloading Data
Then, the function for downloading the ICESat-2 data is called. The download is done using the icepyx package and unfortunately the download using icepyx often crashes due to timeout of request. The solution is to either keep trying until the download is successful, or make the amount of data for download smaller - for example download each year separately. This function downloads the data based on the input settings - _label_, _products_ and _date_range_. The data we downloaded was for the whole Svalbard (label = 'svalbard'), the data products ATL06 and ATL08 (even though ATL06 is most likely enough) and date range from 1.11.2018 to 31.10.2023 (5 hydrological years). The code has the functionality to download ATL03, ATL06, ATL08 and ATL08QL (quicklook) data, reccommended usage is downloading ATL06 or ATL08 or their combination. The raw data is saved to the file 'data/raw/' and a subfolder named by the product (these folders are created automatically in the script, so don't worry about having to create the structure on your own). The files are in .hdf5 format.

### 4. Reading data
The ICESat-2 data is downloaded as .hdf5 files so we need to convert that to something we can work with in Python (pandas dataframe). For that the function read_icesat() is called which loops through the .hdf5 files, saves chosen variables to a dictionary which is then converted to a pandas dataframe. This function was taken and modified from Désirée Treichler. The variables we extracted are: latitude, longitude, height, acquisition time, quality flag (ATL06), but it is possible to look into the data product dictionaries of ATL06 and ATL08 and add variables (by modifying code in the file read_icesat.py). The .csv files for each individual product is saved in the temporary folder temp/ and the merged data for all the products is saved as temp/ICESat.csv.

### 5. Computing elevation change
Elevation change is computed between each of the ICESat-2 heights and elevation on the reference DEM, which is in this case a mosaic of DEMs from the Norwegian Polar Institute (NPI). The NPI DEMs are warped and saved as a vrt using the build_dem.py script that is taken from Erik Schytt Mannerfelt. It is necessary to have the DEMs downloaded and saved in 'cache/'. Elevation change has to be corrected by ~30m which is the difference between ICESat-2 heights (above WGS-84 ellipsoid) and the NPI DEM (above geoid) in Svalbard. 

### 6. Select Glaciers
Glaciers within the area of interest (variable 'label') are selected from the Randolph Glacier Inventory (RGI). A geopackage with the clipped RGI is saved in the 'data/' folder. A list of glaciers is stored in a variable, which will then be looped through in the next steps.

### 7. Create glacier subsets
Clips the ICESat-2 data and saves a new geopackage for each glacier. The subsets are saved in 'temp/glaciers/' with the naming convention 'glacierID_icesat_clipped.gpkg'.

### 8. Filtering and Normalizing
Filters the ICESat-2 data from noise (mainly caused by clouds). The filtering is done using the RANSAC algorithm on 2D data where the x-dimension is ICESat-2 height and the y-dimension is elevation from the NPI DEM. This enables us to remove clouds while keeping the points for surges.

The elevation data is normalized (not the elevation change) to 0-1 for each glacier so that the classification result is not affected by some glaciers being higher above sea level than others.

### 9. Grouping by Hydrological Years
The last step before the classification is to split the year data by hydrological years. A hydrological year begins on 1.11. and ends on 31.10. The files are stored in 'temp/glaciers/' with a naming convention 'glacierID_year.gpkg' where year 2019 means the hydrological year beginning on 1.11.2018 and ending 31.10.2019.

### 10. Extract Features and Count Yearly Changes
Features to describe elevation change trends over the glacier were extracted. Most of them are visualized on the plots below (Andrinebreen - stable glacier, Austfonna - surging glacier). These features served as input to the Random Forest Classification. Subsequently, the yearly changes were computed on all the features. 
![statisticalmetricsAndrinebreen2019](https://github.com/user-attachments/assets/d0dad9b3-a7c9-49d9-bfd0-f1bd15752516)
![statisticalmetricsAustfonna, -2020](https://github.com/user-attachments/assets/c51db768-f804-458c-94d0-1867554b0619)

### 11. Random Forest Classification
A Random Forest Classification is computed based on training data from Kääb et al. (2023). The training data can be downloaded in this Github project and should be saved in the 'data' folder. A confusion matrix is computed and saved in the results folder as a .png file.
![confusionmatrix_RF_svalbard_2024-07-21_bin](https://github.com/user-attachments/assets/7e98a3de-8f98-40f8-a98f-383218682855)

Results of the classification are saved as a geopackage with the attributes glacier_id, year, glacier_name, geometry, surging (binary), probability (probability that it belongs to the assigned class). Furthermore, the results are split into files 

### 12. Plot Results
Maps of results are created for each year and saved in the 'results' folder.
![results2019probs1](https://github.com/user-attachments/assets/46568b5c-f6fc-4e9c-8767-a6191a5116e9)


## Acknowledgements and Credits
This project was developed in collaboration with people at the University in Oslo, namely Erik Schytt Mannerfelt and Désirée Treichler. Some parts of the code are taken directly from them (when this is the case, it is directly stated in a comment in the code). This project was created as part of my diploma thesis at the Charles University in Prague.
