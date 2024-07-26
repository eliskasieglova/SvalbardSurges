import pandas as pd
import geopandas as gpd
from vars import label
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, precision_score, recall_score,  f1_score
from sklearn.model_selection import train_test_split
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

def confusionMatrix(y_training_data, y_pred):
    """
    Create and save confusion matrix.
    """

    # Get and reshape confusion matrix d/ata
    matrix = confusion_matrix(y_training_data, y_pred)
    matrix = matrix.astype('float') / matrix.sum(axis=1)[:, np.newaxis]
    # Build the plot
    plt.figure(figsize=(16, 7))
    sns.set(font_scale=1.4)
    sns.heatmap(matrix, annot=True, annot_kws={'size': 18},
                cmap=plt.cm.Blues, linewidths=0.2)
    # Add labels to the plot
    class_names = ['not_surging', 'surging']
    tick_marks = np.arange(len(class_names))
    tick_marks2 = tick_marks + 0.5
    plt.xticks(tick_marks, class_names, rotation=25)
    plt.yticks(tick_marks2, class_names, rotation=0)
    plt.xlabel('Predicted label')
    plt.ylabel('True label')
    plt.title(f'Confusion Matrix for Random Forest Model')
    plt.savefig(f'figs/confusionmatrix.png')
    plt.close()


def RF(data, training_data):
    """
    Classifies input data by supervised Random Forest.

    Params:
    - data
        input data to be classified (DataFrame)
    - training data
        training dataset used for classification (including all computed features) (DataFrame)

    Returns:
    Previous DataFrame "data" with an additional column "surging" predicted using Random Forest.
    """

    # remove nans from datasets
    data_all = data
    data = data.dropna(axis='index')
    training_data = training_data.dropna(axis='index')

    # Split the data into features (X) and target (y)
    X = data.drop(columns=['id', 'glacier_id', 'year', 'quality_flag'])

    # split training dataset into training and validation dat
    X_training_data = training_data.drop(columns=['id', 'surging'])
    y_training_data = training_data.surging

    # cross validation
    # separate training dataset to training and test data
    X_train, X_test, y_train, y_test = train_test_split(X_training_data, y_training_data, test_size=0.3)

    # cross validation
    from sklearn.model_selection import cross_val_score
    rf = RandomForestClassifier()
    scores = cross_val_score(rf, X_train, y_train, cv=3)
    print(f'Accuracies: {scores}')
    scores = cross_val_score(rf, X_train, y_train, cv=3, scoring='precision')
    print(f'Precisions: {scores}')
    scores = cross_val_score(rf, X_train, y_train, cv=3, scoring='recall')
    print(f'Recalls: {scores}')
    scores = cross_val_score(rf, X_train, y_train, cv=3, scoring='f1')
    print(f'F1-Scores: {scores}')

    # create classification based on whole training dataset
    rf = RandomForestClassifier(n_estimators=100, min_samples_split=20, max_depth=80, random_state=1)
    rf.fit(X_train, y_train)
    y_pred = rf.predict(X_training_data)

    # save figure of confusion matrix
    confusionMatrix(y_training_data, y_pred)

    r = {}

    for i in range(1, 6):
        # create classification based on whole training dataset
        rf = RandomForestClassifier(n_estimators=100, min_samples_split=20, max_depth=80, random_state=i)
        rf.fit(X_training_data, y_training_data)

        # create dataframe for glaciers that were in the classification
        r[f'surging_{i}'] = rf.predict(X)
        r[f'probability_{i}'] = [x[0] if (x[0] > x[1]) else x[1] for x in rf.predict_proba(X)]

    for i in range(1, 6):
        X[f'surging_{i}'] = r[f'surging_{i}']
        X[f'probability_{i}'] = r[f'probability_{i}']

    result = pd.concat([data, X], axis=1, join='inner')
    result['probability'] = (result[[f'probability_{x}' for x in range(1, 6)]]).sum(axis=1) / 5
    result['sum'] = (result[[f'surging_{x}' for x in range(1, 6)] ]).sum(axis=1)
    result['surging'] = np.where(result['sum'] > 2, 1, 0)
    # create dataframe for empty glaciers (none, were not in classification)

    # Merge the dataframes
    merged_df = pd.merge(data_all, data, on=['glacier_id', 'year'], how='left', indicator=True)

    # Filter the rows where the indicator is 'left_only' (i.e., only in all_glaciers)
    empty_glaciers = merged_df[merged_df['_merge'] == 'left_only']

    # Select only the necessary columns
    empty_glaciers = empty_glaciers[['year', 'glacier_id']]
    empty_glaciers['id'] = empty_glaciers['glacier_id'] + '_' + empty_glaciers['year'].astype(str)
    empty_glaciers['surging'] = -999

    # only return surge/not surge
    subset = result[['id', 'glacier_id', 'year',
                     'surging_1', 'surging_2', 'surging_3', 'surging_4', 'surging_5',
                     'probability_1', 'probability_2', 'probability_3', 'probability_4', 'probability_5',
                     'surging', 'probability']]

    # merge with empty glaciers
    subset = pd.concat([subset, empty_glaciers])

    return subset


def classify():
    """
    Classify using Random Forest. Reads the training data and saves the result based on
    chosen variables in vars.py.

    :param data: dataframe with extracted features, glacier_id, geometry

    """
    # read input data
    data = gpd.read_file(f'temp/{label}_features_dy.gpkg', engine='pyogrio', use_arrow=True)

    # assign id
    data['id'] = data['glacier_id'] + '_' + data['year'].astype(str)

    # read training data
    training_data = pd.read_csv(f'data/trainingdata.csv', engine='pyarrow')

    rf_variables = ['glacier_id',
                    'year',
                    'quality_flag',
                    'id',
                    'dh_max_l',
                    'dh_mean_l',
                    'dh_std',
                    'dh_std_l',
                    'hdh_std',
                    'hdh_std_l',
                    'lin_coef_binned',
                    'lin_coef_l_binned',
                    'variance_dh',
                    'variance_dh_l',
                    'correlation',
                    'correlation_l',
                    'ransac',
                    'ransac_l',
                    'over15',
                    'bin1',
                    'bin2',
                    'bin3',
                    'bin4',
                    'bin5',
                    'bin6',
                    'bin7',
                    'bin8',
                    'bin9',
                    'bin10',
                    'bin11',
                    'bin12',
                    'bin13',
                    'bin14',
                    'bin15',
                    'bin16',
                    'bin17',
                    'bin18',
                    'residuals',
                    'bin_max',
                    'surging']

    # select the data subset
    training_data = pd.merge(data, training_data, on=['glacier_id', 'year'])
    print(len(training_data))

    # filter out the bad quality flags
    training_data = training_data[training_data['quality_flag'] > 1]
    print(len(training_data))

    # add unique ID (combo of glacier ID and year)
    training_data['id'] = training_data['glacier_id'] + '_' + training_data['year'].astype(str)

    # prepare training data and input data for Random Forest
    training_data = training_data[rf_variables[3:]]
    input_data = data[rf_variables[:-1]]

    result = RF(input_data, training_data)

    # merge results of RF with original data
    result = pd.merge(data, result, on=['glacier_id', 'year', 'id'])
    result = result[['glacier_id', 'glac_name', 'year',
                     'surging', 'probability',
                     'surging_1', 'surging_2', 'surging_3', 'surging_4', 'surging_5',
                     'probability_1', 'probability_2', 'probability_3', 'probability_4', 'probability_5',
                     'geometry', 'quality_flag']]
    result = result.rename(columns={'glac_name': 'glacier_name'})

    # append if the glacier was in the training data
    training_column = []
    for i in range(len(result)):
        glacier_id = result['glacier_id'].iloc[i]
        year = result['year'].iloc[i]
        subset = training_data[training_data['id'] == f'{glacier_id}_{year}']

        if len(subset) == 1:
            training_column.append(1)
        else:
            training_column.append(0)

    result['training'] = training_column

    # convert df to gdf
    result = gpd.GeoDataFrame(result)
    result.to_file(f'results/Results.gpkg')
    # save data
    r_4326 = result.to_crs(4326)
    r_4326.to_file(f'results/Results.geojson')

    # split data by year and save as individual files
    for year in [2019, 2020, 2021, 2022, 2023]:
        subset = result[result['year'] == year]
        subset.to_file(f'results/Results_{year}.gpkg')
        s_4326 = subset.to_crs(4326)
        s_4326.to_file(f'results/Results_{year}.geojson')
        print(year)
        print(len(subset[subset['surging'] == 1]))

    return result

