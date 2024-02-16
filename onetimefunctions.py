import pandas as pd


def convertTrainingData():
    """
    Convert table from Erik to table with same structure as my data.

    """
    data_erik = pd.read_csv('data/surge_table.csv')

    # column names for df
    columns = ['glacier_id', 'year']

    # data that will go as input for df has to be in tuples
    data = []

    for index, row in data_erik.iterrows():
        # if surge was ongoing for more than 1
        #if (row['end_year'] - row['start_year']) > 1:

        # if only 1 year is in the table (start year or end year)
        #if (row['start_year'] == None) & (row['start_year'] == None):
        tpl = [row['glims_id'], row['']]
        data.append(tpl)

    # create pandas dataframe with same structure as my data
    df = pd.DataFrame(data)










