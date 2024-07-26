import pandas as pd
import time
from matplotlib import pyplot as plt
import geopandas as gpd
from user_vars import label
import contextily as cx
import matplotlib.patches as mpatches
import numpy as np
from scipy.stats import norm
import matplotlib.lines as mlines
import preprocessing
from sklearn import linear_model
import analysis
from glacier_names import glacier_names
import matplotlib.patheffects as pe
import matplotlib.colors as mcolors


def plotDataLoc():
    """
    Plots the datapoints (ATL06, ATL08, ATL08QL) to see what area they cover.
    Does not include ATL03 because it took forever to load...
    """
    start_time = time.time()
    # read data
    atl06 = pd.read_csv('data/atl06.csv')
    print('atl06 loaded', time.time() - start_time)
    atl08 = pd.read_csv('data/atl08.csv')
    print('atl08 loaded', time.time() - start_time)
    atl08ql = pd.read_csv('data/atl08ql.csv')
    print('atl08ql loaded', time.time() - start_time)

    # visualize where they are
    plt.subplots(2, 2)

    print('plotting atl06', time.time() - start_time)
    plt.subplot(2, 2, 2)
    plt.title('ATL06')
    plt.scatter(atl06['longitude'], atl06['latitude'], c=atl06['h'])

    print('plotting atl08', time.time() - start_time)
    plt.subplot(2, 2, 3)
    plt.title('ATL08')
    plt.scatter(atl08['longitude'], atl08['latitude'], c=atl08['h'])

    print('plotting atl08ql', time.time() - start_time)
    plt.subplot(2, 2, 4)
    plt.title('ATL08QL')
    plt.scatter(atl08ql['longitude'], atl08ql['latitude'], c=atl08ql['h'])
    print(time.time() - start_time)

    plt.tight_layout()
    plt.show()


def plotResults(results):
    """
    Plot results. Function made for the years 2020, 2021, 2022 and tested on the area of Heerland.

    :param results: Result DataFrame with columns ['year', 'surging', 'geometry'].

    :return: Saves plot to temp/fig folder.
    """

    results2020 = results[results['year'] == 2018]
    results2020 = results[results['year'] == 2019]
    results2020 = results[results['year'] == 2020]
    results2021 = results[results['year'] == 2021]
    results2022 = results[results['year'] == 2022]
    results2022 = results[results['year'] == 2023]

    #2020
    surging = results2020[results2020['surging'] == 1]
    not_surging = results2020[results2020['surging'] == 0]

    ax = surging.boundary.plot(color='darkred')
    not_surging.boundary.plot(color='darkblue', ax=ax)
    cx.add_basemap(ax, crs=results2021.crs.to_string(), source=cx.providers.Esri.WorldImagery)

    txt = ax.texts[-1]
    txt.set_position([0.5, -0.1])
    txt.set_ha('center')
    txt.set_va('bottom')

    ax.set_axis_off()
    plt.axis('equal')
    plt.title('2020')

    surgingpatch = mpatches.Patch(color='darkred', label='surging')
    notsurgingpatch = mpatches.Patch(color='darkblue', label='not surging')
    plt.legend(handles=[surgingpatch, notsurgingpatch], loc=(0.8, 0.8))

    plt.savefig(f'temp/figs/results_{label}_2020.png')

    # 2021
    surging = results2021[results2021['surging'] == 1]
    not_surging = results2021[results2021['surging'] == 0]

    ax = surging.boundary.plot(color='darkred')
    not_surging.boundary.plot(color='darkblue', ax=ax)
    cx.add_basemap(ax, crs=results2021.crs.to_string(), source=cx.providers.Esri.WorldImagery)

    txt = ax.texts[-1]
    txt.set_position([0.5, -0.1])
    txt.set_ha('center')
    txt.set_va('bottom')

    ax.set_axis_off()
    plt.axis('equal')
    plt.title('2021')

    surgingpatch = mpatches.Patch(color='darkred', label='surging')
    notsurgingpatch = mpatches.Patch(color='darkblue', label='not surging')
    plt.legend(handles=[surgingpatch, notsurgingpatch], loc=(0.8, 0.8))

    plt.savefig(f'figs/results_{label}_2021.png')

    # 2022
    surging = results2022[results2022['surging'] == 1]
    not_surging = results2022[results2022['surging'] == 0]

    ax = surging.boundary.plot(color='darkred')
    not_surging.boundary.plot(color='darkblue', ax=ax)
    cx.add_basemap(ax, crs=results2022.crs.to_string(), source=cx.providers.Esri.WorldImagery)

    txt = ax.texts[-1]
    txt.set_position([0.5, -0.1])
    txt.set_ha('center')
    txt.set_va('bottom')

    ax.set_axis_off()
    plt.axis('equal')
    plt.title('2022')

    surgingpatch = mpatches.Patch(color='darkred', label='surging')
    notsurgingpatch = mpatches.Patch(color='darkblue', label='not surging')
    plt.legend(handles=[surgingpatch, notsurgingpatch], loc=(0.8, 0.8))

    plt.savefig(f'data/temp/figs/results_{label}_2022.png')


def plotRTG(glacier_id):
    # plot repeat ground tracks for the years - data i have

    glacier_name = glacier_names[glacier_id]
    shp = gpd.read_file(f'temp/glaciers/{glacier_id}.gpkg')

    years = [2019, 2020, 2021, 2022, 2023]

    fig, ax = plt.subplots()
    shp.boundary.plot(ax=ax, color='black')
    for year in years:
        data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
        ax.scatter(data.easting, data.northing, s=0.1, label=year)
        cx.add_basemap(ax, crs=data.crs.to_string(), source=cx.providers.Esri.WorldImagery)

        txt = ax.texts[-1]
        txt.set_position([0.5, -1])
        txt.set_ha('center')
        txt.set_va('bottom')

    ax.set_axis_off()
    plt.legend()
    plt.axis('equal')
    plt.title(f'RGT on {glacier_name}')
    plt.show()


def whatIsWrongWithATL06(data):
    import matplotlib.pyplot as plt
    import geopandas as gpd
    import pandas as pd
    import os
    import contextily as cx

    atl06 = pd.read_csv('data/ATL06.csv')
    #a = atl06.where(atl06['dh'] > -100).dropna()
    b = atl06.where((atl06['dh'] < -500) | (atl06['dh'] > 500)).dropna()
    shp = gpd.read_file('data/SJM_adm0.shp')

    fig, ax = plt.subplots()
    #ax.scatter(a.easting, a.northing, c='yellow', s=2, marker='.')
    ax.scatter(b.easting, b.northing, c='blue', s=2, marker='.')
    cx.add_basemap(ax, crs=32633, source=cx.providers.Esri.WorldImagery)
    plt.xlim(b.easting.min(), b.northing.max())
    plt.ylim(b.easting.min(), b.northing.max())
    plt.axis('equal')
    plt.savefig('figs/whatiswrongwithatl06.png')

    return


def plotElevationPointsOnGlacier(glacier_id):
    # visualize glacier with elevation points on top
    shp = gpd.read_file(f'temp/glaciers/{glacier_id}.gpkg')
    d = gpd.read_file(f'temp/glaciers/{glacier_id}_2022.gpkg')

    shp.plot(color='whitesmoke', edgecolor='black')
    scatter = plt.scatter(d.easting, d.northing, c=d.dem_elevation, s=2, marker='.', label='elevation', cmap='rainbow')
    cbar = plt.colorbar(scatter, label='elevation (h)')
    plt.title('Monacobreen, 2022')
    plt.savefig('figs/vish.png')
    plt.close()

    # plot same but dh
    shp.plot(color='whitesmoke', edgecolor='black')
    scatter = plt.scatter(d.easting, d.northing, c=d.dh, s=2, marker='.', label='elevation', cmap='Spectral_r')
    cbar = plt.colorbar(scatter, label='elevation change (dh)')
    plt.title('Monacobreen, 2022')
    plt.savefig('figs/visdh.png')
    plt.close()


def plot_h_dh(glacier_id, year, dem_year):
    # plot basic h/dh plots

    # not surging glacier
    data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')

    scatter = plt.scatter(data.dem_elevation, data.dh, s=1.5, marker='.', c='darkgreen')
    plt.title(f'{glacier_names[glacier_id]}, 2019')
    plt.xlabel('elevation (%)')
    plt.ylabel('elevation change (m)')
    plt.ylim(-75, 75)
    plt.xlim(0, 1)
    plt.savefig('figs/visns.png')
    plt.close()

    plt.ylim(-75, 75)
    plt.xlim(0, 1)
    plt.savefig('figs/viss.png')
    plt.close()

    return


def plotTrainingVariables():

    data = pd.read_csv('temp/trainingdata_features.csv')
    vars = list(data.columns)

    for var in vars:
        plt.scatter(data.index, data[var], c=data.surging)
        plt.title(var)
        plt.savefig('figs/var.png')
        plt.close()


def plotTrainingDataPoints():

    data = pd.read_csv('temp/trainingdata_features.csv')
    colors = ['teal', 'crimson']

    for i in range(len(data)):
        # save the vars i will need
        row = data.iloc[i]
        glacier_id = row['glacier_id']
        glacier_name = row['name']
        year = row['year']
        surging = int(row['surging'])
        color = colors[surging]

        # open the point data
        d = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
        plt.scatter(d.h_norm, d.dh, s=2, c=color)
        plt.xlim(0, 1)
        plt.ylim(-75, 75)
        plt.title(f'{glacier_name}, {glacier_id}, {year}, {surging}')
        plt.savefig(f'temp/trainingdata/figs/{glacier_name}_{glacier_id}_{year}_{surging}.png')
        plt.close()


def plotRGIBySurgeType():
    # plot RGI, color by surge type

    # load RGI
    rgi = gpd.read_file(f'data/rgi_{label}.gpkg')

    # load Svalbard shp
    shp = gpd.read_file('data/SJM_adm0.shp')
    shp = shp.to_crs(32633)

    # plot svalbard outline
    ax = shp.plot(edgecolor='black')
    cx.add_basemap(ax, crs=shp.crs.to_string(), source=cx.providers.Esri.WorldImagery)

    # list of colors to use
    colors = ['deepskyblue', 'crimson', 'crimson', 'crimson']
    alphas = [0.4, 0.25, 0.5, 1]

    # add new column for color
    rgi['surge_color'] = [colors[x] for x in rgi.surge_type]
    rgi['alpha'] = [alphas[x] for x in rgi.surge_type]

    # plot RGI, color by variable
    rgi.plot(color=rgi['surge_color'], ax=ax, alpha=rgi['alpha'])

    # add legend
    notobserved = mpatches.Patch(color=colors[0], label='not observed', alpha=0.4)
    possible = mpatches.Patch(color=colors[1], label='possible', alpha=0.25)
    probable = mpatches.Patch(color=colors[2], label='probable', alpha=0.5)
    observed = mpatches.Patch(color=colors[3], label='observed')
    plt.legend(handles=[notobserved, possible, probable, observed], loc=(0.9, 0.1))

    # format plot
    plt.title('RGI by Surge Type')
    plt.xlim(300000, 950000)  # rozsah x-axis
    plt.ylim(8400000, 9050000)  # rozsah y-axis
    #plt.axis('off')

    # save and close
    #plt.savefig('figs/rgisurgetype.png')
    #plt.close()
    plt.show()

    return


def plotRGIByTerminusType():
    # plot RGI, color by surge type

    # load RGI
    rgi = gpd.read_file(f'data/rgi_{label}.gpkg')

    # load Svalbard shp
    svalbard = gpd.read_file('data/SJM_adm0.shp')
    svalbard = svalbard.to_crs(32633)

    # plot svalbard outline
    ax = svalbard.plot(color='whitesmoke', edgecolor='black')

    # list of colors to use
    colors = {1: 'deepskyblue',
              9: 'crimson'}

    # add new column for color
    rgi['terminus_color'] = [colors[x] for x in rgi.term_type]

    # plot RGI, color by variable
    rgi.plot(color=rgi['terminus_color'], ax=ax, alpha=0.75)

    # add legend
    marine = mpatches.Patch(color=colors[1], label='marine terminating', alpha=0.75)
    land = mpatches.Patch(color=colors[9], label='land terminating', alpha=0.75)
    plt.legend(handles=[marine, land], loc=(0.8, 0.1))

    # format plot
    plt.title('RGI by Terminus Type')
    plt.xlim(300000, 950000)  # rozsah x-axis
    plt.ylim(8400000, 9050000)  # rozsah y-axis
    plt.axis('off')

    # save and close
    plt.savefig('figs/rgiterminustype.png')
    plt.close()


    return


def trainingDataHistograms(var, varname, xlab):

    data = gpd.read_file(f'temp/{label}_features.gpkg', engine='pyogrio', use_arrow=True)
    training_data = pd.read_csv('data/trainingdata_histograms.csv', engine='pyarrow')
    training_data = pd.merge(data, training_data, on=['glacier_id', 'year'])

    subset = training_data[['glacier_id', 'year', var, 'surging']]
    subset = subset.dropna(axis='columns')
    subset = subset.dropna()

    # split data into surging and not surging
    s = subset[subset['surging'] == 1]
    ns = subset[subset['surging'] == 0]


    # plot histogram
    #plt.hist([s[var], ns[var]], color=['red', 'darkblue'], label=['surging', 'not surging'], bins=30, density=[True, True], alpha=0.6, zorder=100)
    bins = np.linspace(-100, 100, 50)
    plt.hist(s[var], color='red', label='surging', bins=bins, density=True, alpha=0.4, zorder=100)
    plt.hist(ns[var], color='darkblue', label='not surging', bins=bins, density=True, alpha=0.4, zorder=100)
    # grid
    plt.grid(visible=False, color='w', linestyle='-', linewidth=0.5, zorder=-2)
    plt.gca().patch.set_facecolor('0.9')

    # plot distribution curves
    x = np.linspace(-100, 100, 200)  # surging
    mu, std = norm.fit(s[var])
    p = norm.pdf(x, mu, std)
    plt.plot(x, p, linewidth=2, c='red', path_effects=[pe.Stroke(linewidth=3, foreground='w'), pe.Normal()],
             zorder=101, label='surging')

    x = np.linspace(-100, 100, 200)  # not surging
    mu, std = norm.fit(ns[var])
    p = norm.pdf(x, mu, std)
    plt.plot(x, p, linewidth=2, c='darkblue', path_effects=[pe.Stroke(linewidth=3, foreground='w'), pe.Normal()],
             zorder=101, label='not surging')

    # format
    plt.title(f'distribution of {varname}')  # add title
    plt.legend(loc='upper right')  # add legend

    plt.xlim(-100, 100)
    plt.xlabel(xlab)
    plt.ylabel('frequency')
    #plt.yticks([0, 20, 40, 60, 80, 100], [0, 0.2, 0.4, 0.6, 0.8, 1])

    # save and close figure
    plt.savefig(f'figs/histogram_{var}.png')
    plt.close()


def plotPointsFromTrainingDataset():
    # plot h/dh for all glaciers in training dataset, color surging/not surging differently

    trainingdata = pd.read_csv('data/trainingdata.csv')

    # set colors for plotting surging/non surging data
    colors = ['darkblue', 'crimson']

    l = len(trainingdata)
    for i in range(l):
        print(f'{i}/{l}')
        glacier_id = trainingdata['glacier_id'].iloc[i]
        color = colors[int(trainingdata['surging'].iloc[i])]

        # open point data
        try:
            data = pd.read_file(f'temp/glaciers/{glacier_id}_icesat.csv')
        except:
            try:
                data = gpd.read_file(f'temp/glaciers/{glacier_id}_filtered_ATL08.gpkg')
                data.to_csv(f'temp/glaciers/{glacier_id}_icesat.csv')
            except:
                print(f'{glacier_id} work')
                continue

        # plot h/dh
        plt.scatter(data.h_norm, data.dh, s=1, marker='.', c=color, alpha=0.75)

    # legend
    surging_pt = mlines.Line2D([], [], color='crimson', marker='.', linestyle='None', markersize=4, label='surging')
    nonsurging_pt = mlines.Line2D([], [], color='teal', marker='.', linestyle='None', markersize=4, label='not surging')
    plt.legend(handles=[surging_pt, nonsurging_pt])

    # format
    plt.xlim(0, 1)
    plt.ylim(-200, 200)
    plt.title('Training Dataset: ICESat-2 Points')
    plt.xlabel('elevation (normalized)')
    plt.ylabel('elevation change (m)')

    # save and close
    plt.savefig('figs/trainingdata.png')

    return


def plotLinRegComparison(var, var_name):
    # load training data
    trainingdata = gpd.read_file('temp/trainingdata/trainingdata_features.gpkg')

    # choose glaciers and years
    s_id = 'G015037E77377N'  # surging id (Recherchebreen)
    s_year = 2019  # surging year
    ns_id = 'G018010E77975N'  # non surging id
    ns_year = 2019  # non surging year

    # load the data
    s_features = trainingdata[trainingdata['glacier_id'] == s_id]
    s_features = s_features[s_features['year'] == s_year]
    ns_features = trainingdata[trainingdata['glacier_id'] == ns_id]
    ns_features = ns_features[ns_features['year'] == ns_year]

    # load glacier names
    s_name = 'Recherchebreen'
    ns_name = 'Andrinebreen'

    # load pts
    s_pts = gpd.read_file(f'temp/glaciers/{s_id}_{s_year}.gpkg')
    ns_pts = gpd.read_file(f'temp/glaciers/{ns_id}_{ns_year}.gpkg')

    # initiate plot
    fig, axs = plt.subplots(1, 2, figsize=(15, 15))

    # left plot - surging glacier
    plt.subplot(1, 2, 1)
    plt.scatter(s_pts.h_norm, s_pts.dh, s=1.5, marker='.', c='lightsteelblue', alpha=0.4, label='surging')  # plot the data points
    # plot linear regression
    X = s_pts.h_norm.values.reshape(-1, 1)
    y = s_pts.dh.values.reshape(-1, 1)
    lr = linear_model.LinearRegression()
    lr.fit(X, y)
    line_X = np.arange(0, 1, 0.05).reshape(-1, 1)
    line_y = lr.predict(line_X)
    plt.plot(line_X, line_y, color="royalblue", linewidth=3, label="Linear Regressor: Surging")

    plt.legend(loc='upper right')
    plt.text(0.8, -135, f'coef={round(lr.coef_[0][0], 2)}')
    plt.title(f'Surging Glacier\n{s_name} ({s_year})')
    plt.xlim(0, 1)
    plt.ylim(-150, 100)

    # right plot - non-surging glacier
    plt.subplot(1, 2, 2)
    plt.scatter(ns_pts.h_norm, ns_pts.dh, s=1.5, marker='.', c='lightsteelblue', alpha=0.4, label='non-surging')
    X = ns_pts.h_norm.values.reshape(-1, 1)
    y = ns_pts.dh.values.reshape(-1, 1)
    lr = linear_model.LinearRegression()
    lr.fit(X, y)
    line_X = np.arange(0, 1, 0.05).reshape(-1, 1)
    line_y = lr.predict(line_X)
    plt.plot(line_X, line_y, color="royalblue", linewidth=3, label="Linear Regressor: Non-Surging")

    plt.legend(loc='upper right')
    plt.text(0.8, -135, f'coef={round(lr.coef_[0][0], 2)}')
    plt.title(f'Non-Surging Glacier\n{ns_name} ({ns_year})')  # title
    plt.xlim(0, 1)  # limits
    plt.ylim(-150, 100)  # limits

    plt.suptitle('Linear Regression Coefficients')
    plt.tight_layout()
    plt.savefig('figs/linregcomparison.png')
    plt.close()


def plotResultsSubplots():

    # load results
    results = gpd.read_file(f'results/results_svalbard.gpkg')

    # add surge color column
    colors = {
        1: 'crimson',
        0: 'deepskyblue',
        -999: 'grey'
    }
    alfa = 0.6
    results['surge_color'] = [colors[x] for x in results['surging']]

    # create subsets for each year
    rf18 = results[results['year'] == 2018]
    rf19 = results[results['year'] == 2019]
    rf20 = results[results['year'] == 2020]
    rf21 = results[results['year'] == 2021]
    rf22 = results[results['year'] == 2022]
    rf23 = results[results['year'] == 2023]

    # load svalbard shapefile
    shp = gpd.read_file('data/SJM_adm0.shp').to_crs(32633)

    # create fig for 5 subplots
    fig, ax = plt.subplots(2, 3, sharey='all', sharex='all', figsize=(40, 40))

    # axis limits
    xlim_lower = 300000
    xlim_upper = 950000
    ylim_lower = 8400000
    ylim_upper = 9050000

    years = [2018, 2019, 2020, 2021, 2022, 2023]
    datasets = [rf18, rf19, rf20, rf21, rf22, rf23]
    axes = []

    for i in range(len(years)):
        plt.subplot(2, 3, i+1)

        # set current axis - didnt find better way to do this... :(
        if i+1 == 1:
            axis = ax[0][0]
        elif i+1 == 2:
            axis = ax[0][1]
        elif i+1 == 3:
            axis = ax[0][2]
        elif i+1 == 4:
            axis = ax[1][0]
        elif i+1 == 5:
            axis = ax[1][1]
        elif i+1 == 6:
            axis = ax[1][2]

        # plot
        plt.title(years[i])  # title
        shp.plot(ax=axis, color='whitesmoke', edgecolor='black')  # plot svalbard outline
        datasets[i].plot(ax=axis, color=datasets[i]['surge_color'], alpha=alfa)  # plot RF results
        plt.xlim(xlim_lower, xlim_upper)  # x-axis limits
        plt.ylim(ylim_lower, ylim_upper)  # y-axis limits
        plt.axis('off')

    # final formatting
    plt.suptitle(f'Results')
    plt.tight_layout()

    # save and close
    plt.savefig(f'figs/results.png')
    plt.close()


def plotResultsByYear():
    # load results
    results = gpd.read_file(f'results/results.gpkg')


    # set colors based on "surging" column
    colors = {
        1: 'pink',
        0: 'lightblue',
        -999: 'grey'
    }

    # set alphas based on "QF" column
    alphas = {
        0: 0.2,
        1: 0.4,
        2: 0.6,
        3: 1
    }

    # add new columns with color and alpha
    results['color'] = [colors[x] for x in results['surging']]
    results['alpha'] = [alphas[x] for x in results['quality_flag']]

    # change alphas to 1 for nodata glaciers
    for i, value in enumerate(results['surging']):
        if value == -999:
            results['alpha'].iloc[i] = 1

    # create subsets for each year
    rf18 = results[results['year'] == 2018]
    rf19 = results[results['year'] == 2019]
    rf20 = results[results['year'] == 2020]
    rf21 = results[results['year'] == 2021]
    rf22 = results[results['year'] == 2022]
    rf23 = results[results['year'] == 2023]

    # load svalbard shapefile
    shp = gpd.read_file('data/SJM_adm0.shp').to_crs(32633)

    # create fig for 5 subplots
    fig, ax = plt.subplots()
    fig.set_facecolor('black')

    # axis limits
    xlim_lower = 300000
    xlim_upper = 950000
    ylim_lower = 8400000
    ylim_upper = 9050000

    years = [2018, 2019, 2020, 2021, 2022, 2023]
    datasets = [rf18, rf19, rf20, rf21, rf22, rf23]

    for i in range(len(years)):
        year = years[i]

        fig, axis = plt.subplots()
        fig.set_facecolor('black')

        # plot
        plt.title(years[i])  # title
        axis = shp.plot(color='black', edgecolor='lightgrey', linewidth=0.5)  # plot svalbard outline
        datasets[i].plot(ax=axis, color=datasets[i]['color'], alpha=datasets[i]['alpha'],)  # plot RF results
        plt.xlim(xlim_lower, xlim_upper)  # x-axis limits
        plt.ylim(ylim_lower, ylim_upper)  # y-axis limits
        axis.set_facecolor('black')
        #plt.axis('off')

        # final formatting
        plt.suptitle(f'Results {year}')
        plt.tight_layout()

        # save and close
        plt.savefig(f'figs/results{year}.png')
        plt.close()


def plotSurgingGlaciers():

    results = gpd.read_file(f'results/results.gpkg')

    surging = results[results['surging'] == 1]
    glacnum = len(surging)

    for i in range(glacnum):
        print(f'{i}/{glacnum}')
        glacier_id = surging['glacier_id'].iloc[i]
        year = surging['year'].iloc[i]
        data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
        plt.scatter(data.h_norm, data.dh, s=2, c='darkgreen', marker='.')
        plt.xlim(0, 1)
        plt.ylim(-100, 100)
        plt.title(f'{glacier_id} ({year})')

        plt.savefig(f'temp/figs/2021/{glacier_id}_{year}.png')
        plt.close()


def plotSurgeTiming():

    data = gpd.read_file(f'results/results.gpkg')

    glacier_ids = list(np.unique(data.glacier_id))

    for glacid in glacier_ids:
        subset = data[data['glacier_id'] == glacid]
        minyear = subset['year'].min()
        to_delete = subset[subset['year'] != minyear]
        # get index of all the not min years
        idxs = [x for x in to_delete.index]
        data = data.drop(idxs)

    surging = data[data['surging'] == 1]

    return


def plotTimeline():
    """
    Plot timeline of surges. Saves figure 'figs/timeline.png'.
    """

    # load data
    data = gpd.read_file(f'results/results.gpkg')

    # create subset for surging glaciers
    s = data[data['surging'] == 1]

    # create figure
    plt.figure(figsize=(6, 10))
    plt.scatter(s['year'], s['glacier_id'], c='crimson', s=2)

    plt.yticks(fontsize=8)
    plt.xticks([2018, 2019, 2020, 2021, 2022, 2023], fontsize=8)

    plt.title('Timeline of Surges in Svalbard 2018-2023')
    plt.savefig(f'figs/timeline.png')
    plt.close()

    return


def plotYearPoints(glacier_id):
    # to show overlapping and not overlapping ground tracks

    d = gpd.read_file(f'temp/glaciers/{glacier_id}_filtered_ATL08.gpkg')
    shp = gpd.read_file(f'temp/glaciers/{glacier_id}.gpkg')
    d['year'] = [int(str(x)[:4]) for x in d['date']]

    fig, ax = plt.subplots()
    shp.plot(color='whitesmoke', edgecolor='black', ax=ax)
    scatter = ax.scatter(d.easting, d.northing, c=d.year, s=1, marker='o', cmap='Accent')

    legend1 = ax.legend(*scatter.legend_elements(), loc="lower right")
    ax.add_artist(legend1)

    plt.title('Blomstrandbreen')
    plt.savefig(f'figs/plotyearpts_.png')
    plt.close()

    return


def plotFilteringTechniques(glacier_id):

    glacier_name = glacier_names[glacier_id]

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_icesat.gpkg')

    # filter by h
    filtered_h = data[data['h'] < data.dem_elevation+80]
    filtered_h = filtered_h[filtered_h['h'] > filtered_h.dem_elevation-50]

    filtered_ransac = preprocessing.filterWithRANSAC(data, glacier_id, skipcache=True)
    filtered_ATL08 = preprocessing.filterWithATL08(data, glacier_id, skipcache=True)

    datasets = [data, filtered_h, filtered_ransac, filtered_ATL08]
    titles = ['original data', 'filtered (elevation)', 'filtered (RANSAC)', 'filtered (ATL08)']

    fig, ax = plt.subplots(1, 4, sharex='all', sharey='all', figsize=(15, 4))
    i = 0
    for d in datasets:
        plt.subplot(1, 4, i+1)
        plt.scatter(d.dem_elevation, d.dh, c='orange', s=1)
        plt.title(titles[i])
        plt.xlim(0, 1000)
        plt.ylim(-500, 500)
        plt.gca().set_aspect('equal')

        i = i+1

    plt.suptitle(f'Filtering of ATL06 ({glacier_name})')
    plt.tight_layout()

    plt.savefig(f'figs/filteringtechniques_{glacier_name}.png')
    plt.close()

    return


def plotProblemsWithFilteringByRANSAC(glacier_id):

    glacier_name = glacier_names[glacier_id]

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_icesat.gpkg')
    data['index'] = [x for x in data.index]

    fig, ax = plt.subplots(2, 3, figsize=(15, 15), sharey='all')

    columns = ['index', 'easting', 'northing']

    # elevation
    i = 1
    for c in columns:
        plt.subplot(2, 3, i)
        plt.scatter(data[c], data.dem_elevation, c='darkgreen', s=1)
        plt.ylim(-1000, 1800)
        plt.xlabel(c)
        plt.ylabel('elevation')
        plt.title(f'by elevation and {c}')

        i = i+1

    # elevation change
    for c in columns:
        plt.subplot(2, 3, i)
        plt.scatter(data[c], data.dh, c='orange', s=1)
        plt.ylim(-1000, 1800)
        plt.xlabel(c)
        plt.ylabel('elevation change')
        plt.title(f'by elevation change and {c}')
        i = i+1

    plt.suptitle('Sorting Data Points (Wahlenbergerbreen)')
    plt.tight_layout()

    plt.savefig(f'figs/sortingforransac{glacier_name}all.png')
    plt.close()

    # RANSAC
    fig, ax = plt.subplots(2, 3, figsize=(15, 15), sharey='all')

    columns = ['index', 'easting', 'northing']

    # elevation
    i = 1
    for c in columns:
        plt.subplot(2, 3, i)

        X = data[c].values.reshape(-1, 1)
        y = data.dem_elevation.values.reshape(-1, 1)

        ransac = linear_model.RANSACRegressor(max_trials=100)
        ransac.fit(X, y)

        inlier_mask = ransac.inlier_mask_
        outlier_mask = np.logical_not(inlier_mask)

        # Predict data of estimated models (draw the line)
        line_X = np.arange(X.min(), X.max())[:, np.newaxis]
        line_y_ransac = ransac.predict(line_X)

        plt.scatter(X[outlier_mask], y[outlier_mask], color="orange", marker=".", label="Outliers", s=1)
        plt.scatter(X[inlier_mask], y[inlier_mask], color="darkgreen", marker=".", label="Inliers", s=1)

        plt.ylim(-1000, 1800)
        plt.xlabel(c)
        plt.ylabel('elevation')
        plt.title(f'by elevation and {c}')

        i = i+1

    # elevation change
    for c in columns:
        plt.subplot(2, 3, i)

        X = data[c].values.reshape(-1, 1)
        y = data.dh.values.reshape(-1, 1)

        ransac = linear_model.RANSACRegressor(max_trials=100)
        ransac.fit(X, y)

        inlier_mask = ransac.inlier_mask_
        outlier_mask = np.logical_not(inlier_mask)

        # Predict data of estimated models (draw the line)
        line_X = np.arange(X.min(), X.max())[:, np.newaxis]
        line_y_ransac = ransac.predict(line_X)

        plt.scatter(X[outlier_mask], y[outlier_mask], color="orange", marker=".", label="Outliers", s=1)
        plt.scatter(X[inlier_mask], y[inlier_mask], color="darkgreen", marker=".", label="Inliers", s=1)

        plt.ylim(-1000, 1800)
        plt.xlabel(c)
        plt.ylabel('elevation change')
        plt.title(f'by elevation change and {c}')
        i = i+1

    plt.suptitle('Sorting Data Points (Wahlenbergerbreen)')
    plt.tight_layout()

    plt.savefig(f'figs/ransaced{glacier_name}all.png')
    plt.close()



    return


def ransacOnHDH(glacier_id, glacier_name):

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_icesat_clipped.gpkg')

    fig, ax = plt.subplots()

    X = data.dem_elevation.values.reshape(-1, 1)
    y = data.h.values.reshape(-1, 1)

    ransac = linear_model.RANSACRegressor(max_trials=100)
    ransac.fit(X, y)

    inlier_mask = ransac.inlier_mask_
    outlier_mask = np.logical_not(inlier_mask)

    # Predict data of estimated models (draw the line)
    line_X = np.arange(X.min(), X.max())[:, np.newaxis]
    line_y_ransac = ransac.predict(line_X)

    plt.scatter(X[outlier_mask], y[outlier_mask], color="orange", marker=".", label="outliers", s=1)
    plt.scatter(X[inlier_mask], y[inlier_mask], color="darkgreen", marker=".", label="inliers", s=1)

    plt.title(f'RANSAC filtering on elevation NPI DEM / elevation ICESat-2 \n ({glacier_name})')

    plt.xlabel('elevation from NPI DEM (m)')
    plt.ylabel('elevation from ICESat-2 (m)')

    plt.legend()
    plt.grid(color='w', linestyle='-', linewidth=2)
    plt.gca().patch.set_facecolor('0.9')

    plt.savefig(f'figs/filtering_ransac_{glacier_name}.png')
    plt.close()


    return


def plotSurgesByAreaSubplots():

    # dictionary of xlim, ylim for each area
    spatial_extents = {
        "south": [(42000, 62000), (845000, 865000)],
        "northwest": [(39000, 54000), (865000, 889000)],
        "northeast": [(51000, 65000), (865000, 889000)],
        "nordaustlandet": [(53000, 75000), (870000, 895000)],
        "islands": [(60000, 75000), (855000, 875000)]
    }

    # load data
    svalbard = gpd.read_file('data/SJM_adm0.shp')  # necessary to have adm boundary of svalbard as shp from NPI
    results = gpd.read_file(f'results/results.gpkg')

    colors = {
        1: 'pink',
        0: 'lightblue',
        -999: 'grey'
    }

    # set alphas based on "QF" column
    alphas = {
        0: 0.2,
        1: 0.4,
        2: 0.6,
        3: 1
    }

    # add new columns with color and alpha
    results['color'] = [colors[x] for x in results['surging']]
    results['alpha'] = [alphas[x] for x in results['quality_flag']]

    # initiate plot
    fig, axs = plt.subplots(3, 2, figsize=(10, 10))
    #fig.set_facecolor('black')

    i = 1
    for area in spatial_extents:
        ax = plt.subplot(3, 2, i)
        #ax.set_facecolor('black')

        # plot data
        svalbard.plot(ax=ax, color='black', edgecolor='white', linewidth=0.9)
        results.plot(ax=ax, color=results['color'], alpha=results['alpha'])

        # set xlim and ylim
        plt.xlim(spatial_extents[area][0])
        plt.ylim(spatial_extents[area][1])

        plt.axis('equal')

        i = i+1

    plt.savefig(f'figs/resultsareasubplots.png')
    plt.close()

    return


def surgingGlacierVisualization(id, dem_year):

    name = glacier_names[id]

    # select which type of data i want to plot
    allpoints = True
    binned = True
    linreg = False

    # set labels
    x_label = 'normalized elevation'
    y_label = f'elevation change since {dem_year}'

    # read all the datasets
    data18 = gpd.read_file(f'temp/glaciers/{id}_2018.gpkg')
    data19 = gpd.read_file(f'temp/glaciers/{id}_2019.gpkg')
    data20 = gpd.read_file(f'temp/glaciers/{id}_2020.gpkg')
    data21 = gpd.read_file(f'temp/glaciers/{id}_2021.gpkg')
    data22 = gpd.read_file(f'temp/glaciers/{id}_2022.gpkg')
    data23 = gpd.read_file(f'temp/glaciers/{id}_2023.gpkg')

    datasets = [data18, data19, data20, data21, data22, data23]

    fig, axes = plt.subplots(2, 3, sharey=True, sharex=True)
    if allpoints:
        i = 0
        n = 0
        m = 0
        year = 2018
        colors = ['black', 'darkblue', 'green', 'crimson', 'red', 'orange']
        for d in datasets:
            ax = axes[n][m]
            plt.subplot(2, 3, i+1)
            #plt.title(name)
            plt.title(year)

            # plot data points
            plt.scatter(d.dem_elevation, d.dh, s=1.5, label=year)
            plt.xlim(200, 800)
            plt.ylim(-100, 100)

            # remove y-axis ticks for subplots not on left side
            if (i != 0) & (i != 3):
                ax.tick_params(labelleft=False)

            # remove x-axis ticks for subplots not on bottom
            if (i != 3) & (i != 4) & (i != 5):
                ax.tick_params(labelbottom=False)

            # increment
            m = m + 1
            i = i + 1
            year = year + 1

            # if i am at the end of the row then reset the coords of the subplots (n, m)
            if i == 3:
                n = n + 1
                m = 0

    if binned:
        i = 0
        n = 0
        m = 0
        year = 2018
        colors = ['black', 'darkblue', 'green', 'crimson', 'red', 'orange']
        for d in datasets:
            ax = axes[n][m]
            plt.subplot(2, 3, i+1)
            #plt.title(name)
            plt.title(year)

            # plot data points
            bin_limits = [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1]
            X = np.array(analysis.binData(d, bin_limits)).reshape(-1, 1)
            y = np.array([0.05, 0.15, 0.25, 0.35, 0.45, 0.55, 0.65, 0.75, 0.85, 0.95]).reshape(-1, 1)
            plt.scatter(y, X)
            plt.xlim(0, 1)
            plt.ylim(-75, 75)

            # remove y-axis ticks for subplots not on left side
            if (i != 0) & (i != 3):
                ax.tick_params(labelleft=False)

            # remove x-axis ticks for subplots not on bottom
            if (i != 3) & (i != 4) & (i != 5):
                ax.tick_params(labelbottom=False)

            # increment
            m = m + 1
            i = i + 1
            year = year + 1

            # if i am at the end of the row then reset the coords of the subplots (n, m)
            if i == 3:
                n = n + 1
                m = 0
    if linreg:
        i = 0
        # plot linear regression
        for d in datasets:
            plt.subplot(2, 3, i+1)

            # plot linear regression
            try:
                X = d[d['dem_elevation'] < 800].dem_elevation.values.reshape(-1, 1)
                y = d[d['dem_elevation'] < 800].dh.values.reshape(-1, 1)
                lr = linear_model.LinearRegression()
                lr.fit(X, y)
                line_X = np.arange(0, 800, 10).reshape(-1, 1)
                line_y = lr.predict(line_X)
                plt.plot(line_X, line_y, c='orange', linewidth=1)
                i = i + 1
            except:
                i = i + 1
                continue

    plt.suptitle(name)
    fig.supxlabel(x_label)
    fig.supylabel(y_label)
    plt.tight_layout()
    #plt.legend()
    plt.show()
    #plt.savefig(f'figs/{name}_subplots_dh.png')
    #plt.close()


def plotStatisticalMetrics(glacier_id, year, features):

    # fetch the glacier id
    #glacier_id = ids[glacier_name]
    glacier_name = glacier_names[glacier_id]

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
    features = features[features['glacier_id'] == glacier_id]
    features = features[features['year'] == year]

    data_l = data[data['h_norm'] < 0.4]

    fig, ax = plt.subplots(figsize=(10, 8))

    # scatter data
    plt.scatter(data.h_norm, data.dh, s=2, c='cornflowerblue', marker='.', label='ICESat-2 data points')

    # plot line separating upper and lower part
    plt.plot([0.4, 0.4], [-100, 100], linestyle='dashed', c='black', alpha=0.3, label='border between lower and upper part')

    # bins
    X = np.array([features[f'bin{i}'].iloc[0] for i in range(1, 19)]).reshape(-1, 1)
    y = np.array(
        [0.025, 0.075, 0.125, 0.175, 0.225, 0.275, 0.325, 0.375, 0.425, 0.475, 0.525, 0.575, 0.625, 0.675, 0.725, 0.775,
         0.825, 0.875]).reshape(-1, 1)

    X = analysis.fillNansBins(X)

    # regressions - linear
    lr = linear_model.LinearRegression()
    lr.fit(y, X)
    line_X = np.arange(0, 1, 0.05).reshape(-1, 1)
    line_y = lr.predict(line_X)
    plt.plot(line_X, line_y.reshape(-1, 1), c='red', linewidth=3, label='linear regression')

    # regressions - linear lower
    lr = linear_model.LinearRegression()
    X_l = data_l['h_norm'].values.reshape(-1, 1)
    y_l = data_l['dh'].values.reshape(-1, 1)
    lr.fit(X_l, y_l)
    line_X_l = np.arange(0, 0.41, 0.05).reshape(-1, 1)
    line_y_l = lr.predict(line_X_l)
    plt.plot(line_X_l, line_y_l, linewidth=3, c='orange', label='linear regression (lower part)')

    # regressions - ransac
    ransac = linear_model.RANSACRegressor(max_trials=100)
    ransac.fit(X_l, y_l)
    line_y_ransac = ransac.predict(line_X_l)
    plt.plot(line_X_l, line_y_ransac, linewidth=3, color='green', label='RANSAC regression (lower part)')

    # plot dh max and dh mean
    plt.plot([0, 1], [features.dh_max_l.iloc[0], features.dh_max_l.iloc[0]], linestyle='dashed', color='red', alpha=0.3, label='dh max')
    plt.plot([0, 1], [features.dh_mean_l.iloc[0], features.dh_mean_l.iloc[0]], linestyle='dashed', color='orange', alpha=0.3, label='dh mean')

    # scatter bin averages
    plt.plot(y, X, linewidth=2, marker='.', color='blue', label='bin averages')

    # text box with metrics
    text = f'lin_coef: {round(features.lin_coef_binned.iloc[0], 4)} \n' \
           f'lin_coef_l: {round(features.lin_coef_l_binned.iloc[0], 4)} \n' \
           f'residuals: {round(features.residuals.iloc[0], 2)} \n' \
           f'dh_std: {round(features.dh_std.iloc[0], 2)} \n'

    plt.text(0.8, 60, text, bbox=dict(facecolor='white', alpha=0.5))

    # general plot characteristics
    plt.xlim(0, 1)
    plt.ylim(-100, 100)

    plt.legend(loc='lower right')
    plt.title(f'{glacier_name} ({year})')
    plt.xlabel('normalized elevation')
    plt.ylabel('elevation change (m)')

    plt.grid(color='w', linestyle='-', linewidth=2)
    plt.gca().patch.set_facecolor('0.9')

    plt.savefig(f'figs/trainingdata/statisticalmetrics{glacier_name}{year}.png')
    plt.savefig(f'eliskasieglova.github.io/imgs/{glacier_id}_{year}.png')
    plt.close()

    return


def plotdy():
    # plot pts + bins current year and previous year

    features = gpd.read_file('temp/svalbard_features.gpkg')

    glacier_ids = list(features['glacier_id'])
    years = [2020, 2021, 2022, 2023]

    for glacier_id in glacier_ids:
        glacier_name = glacier_names[glacier_id]
        for year in years:
            f = features[features['glacier_id'] == glacier_id]
            f1 = f[f['year'] == year]
            f2 = f[f['year'] == year-1]
            data1 = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
            data2 = gpd.read_file(f'temp/glaciers/{glacier_id}_{year - 1}.gpkg')

            # plot data
            plt.scatter(data1.dem_elevation, data1.dh, s=1.5, c='red', marker='.', label=f'{year}', alpha=0.5)
            plt.scatter(data2.dem_elevation, data2.dh, s=1.5, c='blue', marker='.', label=f'{year-1}', alpha=0.5)

            # plot bins
            """
            X1 = np.array([f1[f'bin{i}'].iloc[0] for i in range(1, 19)]).reshape(-1, 1)
            y1 = np.array(
                [0.025, 0.075, 0.125, 0.175, 0.225, 0.275, 0.325, 0.375, 0.425, 0.475, 0.525, 0.575, 0.625, 0.675,
                 0.725, 0.775,
                 0.825, 0.875]).reshape(-1, 1)
            X2 = np.array([f2[f'bin{i}'].iloc[0] for i in range(1, 19)]).reshape(-1, 1)
            y2 = np.array(
                [0.025, 0.075, 0.125, 0.175, 0.225, 0.275, 0.325, 0.375, 0.425, 0.475, 0.525, 0.575, 0.625, 0.675,
                 0.725, 0.775,
                 0.825, 0.875]).reshape(-1, 1)

            plt.scatter(X1, y1, s=3, c='red', marker='.')
            plt.scatter(X2, y2, s=3, c='blue', marker='.')
            """

            # format plot
            plt.legend()
            plt.xlim(0, 800)
            plt.ylim(-75, 75)
            plt.title(f'{glacier_name} {year-1}-{year}')

            # export
            plt.savefig(f'eliskasieglova.github.io/imgs/{glacier_id}_{year}_dy.png')
            plt.close()


def plotCubify():

    glacier_id = "G015502E77425N"
    year = 2019

    rgi = gpd.read_file('data/rgi_svalbard.gpkg')
    gl_shp = rgi[rgi['glims_id'] == glacier_id]
    gl_pts = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')

    import matplotlib.pyplot as plt

def plotBins():

    features = gpd.read_file(f'temp/svalbard_features.gpkg')
    glacier_ids = features['glacier_id'].to_list()
    years = [2019, 2020, 2021, 2022, 2023]

    for glacier_id in glacier_ids:
        glacier_name = glacier_names[glacier_id]
        for year in years:
            data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')

            # bins
            X = np.array([features[f'bin{i}'].iloc[0] for i in range(1, 19)]).reshape(-1, 1)
            y = np.array(
                [0.025, 0.075, 0.125, 0.175, 0.225, 0.275, 0.325, 0.375, 0.425, 0.475, 0.525, 0.575, 0.625, 0.675, 0.725, 0.775,
                 0.825, 0.875]).reshape(-1, 1)

            X = analysis.fillNansBins(X)

            plt.scatter(data.h_norm, data.dh, c='blue', s=2, alpha=0.6, label='ICESat-2 points')
            plt.scatter(y, X, s=10, label='bin averages', c='orange')
            plt.xlabel('elevation (normalized)')
            plt.ylabel('elevation change (m)')
            plt.xlim(0, 1)
            plt.ylim(-100, 100)
            plt.legend()
            plt.title(f'{glacier_name}, {year}')

            plt.savefig(f'figs/linregs_binned/{glacier_id}_{year}_1.png')
            plt.close()


def plot3DSurge(glacier_id, dem_year, lims, year=None):

    shp = gpd.read_file(f'temp/glaciers/{glacier_id}.gpkg')
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')

    # Extract the x, y coordinates from the shapefile
    shapefile_x = []
    shapefile_y = []

    for geom in shp.geometry:
        if geom.geom_type == 'Polygon':
            x, y = geom.exterior.xy
            shapefile_x.extend(x)
            shapefile_y.extend(y)
        elif geom.type == 'MultiPolygon':
            for poly in geom:
                x, y = poly.exterior.xy
                shapefile_x.extend(x)
                shapefile_y.extend(y)

    if type(year) == int:
        data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
        data = data[data.dh < 70]
        from matplotlib import colors
        divnorm = colors.TwoSlopeNorm(vmin=lims[0], vcenter=0., vmax=lims[1])
        plot = ax.scatter(data.easting, data.northing, data.dh, marker='o', s=1,
                   c=data.dh, cmap='Spectral_r', norm=divnorm)
        fig.colorbar(plot)

    else:
        years = [2019, 2021, 2023]
        for year in years:
            data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
            ax.scatter(data.easting, data.northing, data.dh, marker='o', s=1, label=year)


    ax.plot(shapefile_x, shapefile_y, c='black', label='glacier shape')

    plt.legend()
    plt.title(f'Elevation changes on {glacier_names[glacier_id]} in meters \n'
              f'between reference DEM ({dem_year}) and ICESat-2 heights ({year})')
    plt.xlabel('easting')
    plt.ylabel('northing')
    plt.show()

    plt.close()


def plotRANSAC3D(glacier_id):

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_icesat_clipped.gpkg')

    X = data.dem_elevation.values.reshape(-1, 1)
    y = data.h.values.reshape(-1, 1)
    ransac = linear_model.RANSACRegressor(max_trials=100)
    ransac.fit(X, y)
    inlier_mask = ransac.inlier_mask_
    outlier_mask = np.logical_not(inlier_mask)
    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(data.longitude[inlier_mask], data.latitude[inlier_mask], y[inlier_mask], color="blue", s=1, marker="o",
               label="Inliers")
    ax.scatter(data.longitude[outlier_mask], data.latitude[outlier_mask], y[outlier_mask], color="grey", s=1, marker=".",
               label="Outliers")
    plt.legend()
    plt.title(glacier_names[glacier_id])
    plt.xlabel('longitude')
    plt.ylabel('latitude')
    plt.title(f'RANSAC filtering - {glacier_names[glacier_id]}')
    plt.show()

    plt.close()


def plotRANSAC2D(glacier_id):

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_icesat_clipped.gpkg')

    X = data.h.values.reshape(-1, 1)
    y = data.dh.values.reshape(-1, 1)

    ransac = linear_model.RANSACRegressor(max_trials=100)
    ransac.fit(X, y)
    inlier_mask = ransac.inlier_mask_
    outlier_mask = np.logical_not(inlier_mask)

    plt.scatter(data.h[outlier_mask], data.dh[outlier_mask], color="grey", s=1, marker=".",
               label="Outliers")
    plt.scatter(data.h[inlier_mask], data.dh[inlier_mask], color="blue", s=1, marker="o",
               label="Inliers")

    plt.legend()
    plt.title(glacier_names[glacier_id])
    plt.xlabel('ICESat-2 heights')
    plt.ylabel('elevation change')
    plt.show()

def plotThresholdFilter3D(glacier_id):

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_icesat_clipped.gpkg')

    data_in = data[data['h'] < data.dem_elevation+80]
    data_in = data_in[data_in['h'] > data_in.dem_elevation-80]

    data_out1 = data[data['h'] > data.dem_elevation+80]
    data_out2 = data[data['h'] < data.dem_elevation-80]

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(data_in.longitude, data_in.latitude, data_in.h, color="blue", s=1, marker="o",
               label="Inliers")
    ax.scatter(data_out1.longitude, data_out1.latitude, data_out1.h, color="grey", s=1, marker=".",
               label="Outliers")
    ax.scatter(data_out2.longitude, data_out2.latitude, data_out2.h, color="grey", s=1, marker=".")
    plt.legend()
    plt.title(glacier_names[glacier_id])
    plt.xlabel('longitude')
    plt.ylabel('latitude')
    plt.show()

    plt.close()

from shapely.ops import unary_union


def plot3DFilterWithATL08(glacier_id):

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_icesat_clipped.gpkg')

    data = preprocessing.xy2geom(data, 'h', 'dh', 'computing_geom')
    ref_data = data[data['product'] != 'ATL06']
    ref_data = gpd.GeoDataFrame(ref_data, geometry='computing_geom')
    filter_data = data[data['product'] == 'ATL06']
    filter_data = gpd.GeoDataFrame(filter_data, geometry='computing_geom')

    buffers = ref_data.buffer(20)
    buff = gpd.GeoSeries(unary_union(buffers))

    mask = []
    for i, row in filter_data.iterrows():
        if row['computing_geom'].intersects(buff)[0]:
            mask.append(True)
        else:
            mask.append(False)

    filter_data['mask'] = mask
    inliers = filter_data[filter_data['mask'] == True]
    inliers6 = inliers[inliers['product'] == 'ATL06']
    inliers8 = data[data['product'] == 'ATL08']
    outliers = filter_data[filter_data['mask'] == False]

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(inliers6.longitude, inliers6.latitude, inliers6.h, color="blue", s=1, marker="o",
               label="Inliers")
    #ax.scatter(inliers8.longitude, inliers8.latitude, inliers8.h, color="red", s=5, marker="o",
    #           label="ATL08 data points")
    ax.scatter(outliers.longitude, outliers.latitude, outliers.h, color="grey", s=1, marker=".",
               label="Outliers")
    plt.legend()
    plt.title(glacier_names[glacier_id])
    plt.xlabel('longitude')
    plt.ylabel('latitude')
    plt.show()


def plotSurgingVsNotSurgingDH():
    features = gpd.read_file('temp/svalbard_features.gpkg')

    x = [0.025, 0.075, 0.125, 0.175, 0.225, 0.275, 0.325, 0.375, 0.425, 0.475, 0.525, 0.575, 0.625, 0.675,
         0.725, 0.775, 0.825, 0.875]

    bins_s = [[] for i in range(18)]

    surging = ['G024396E79406N', 'G015616E77394N', 'G024340E79634N', 'G016915E77433N']
    surging_year = [2021, 2020, 2020, 2023]
    not_surging = ['G012572E79241N', 'G017525E77773N', 'G018010E77975N']
    not_surging_year = [2022, 2021, 2019]

    for i in range(len(surging)):
        glacier_id = surging[i]
        year = surging_year[i]

        glacier = features[features['glacier_id'] == glacier_id]
        data = glacier[glacier['year'] == year]

        try:
            y = [data[f'bin{x}'].values[0] for x in range(1, 19)]
        except:
            continue
        i = 0
        for item in y:
            bins_s[i].append(item)
            i = i + 1

        plt.plot(x, y, c='orange', alpha=0.5)

    bins_ns = [[] for i in range(18)]

    for i in range(len(not_surging)):
        glacier_id = not_surging[i]
        year = not_surging_year[i]

        glacier = features[features['glacier_id'] == glacier_id]
        data = glacier[glacier['year'] == year]
        try:
            y = [data[f'bin{x}'].values[0] for x in range(1, 19)]
        except:
            continue
        i = 0
        for item in y:
            bins_ns[i].append(item)
            i = i + 1

        plt.plot(x, y, c='cornflowerblue', alpha=0.5)

    bin_averages_s = [[x for x in bin if str(x) != 'nan'] for bin in bins_s]
    bin_averages_ns = [[x for x in bin if str(x) != 'nan'] for bin in bins_ns]
    bin_averages_s = [sum(bin_averages_s[x]) / len(bin_averages_s[x]) for x in range(18)]
    bin_averages_ns = [sum(bin_averages_ns[x]) / len(bin_averages_ns[x]) for x in range(18)]
    plt.plot(x, bin_averages_s, linewidth=3, c='darkorange', label='surging')
    plt.plot(x, bin_averages_ns, linewidth=3, c='darkblue', label='not surging')

    plt.legend()
    plt.ylim(-80, 80)
    plt.title('plot of elevation change on surging \n and non-surging glaciers')
    plt.xlabel('elevation (normalized)')
    plt.ylabel('elevation change (m a.s.l.)')
    plt.show()


def plot3DClusters():

    features = gpd.read_file('temp/svalbard_features.gpkg')
    training_data = pd.read_csv('data/trainingdata.csv')
    training_data = pd.merge(features, training_data, on=['glacier_id', 'year'])

    var1 = 'ransac_l'
    var2 = 'lin_coef_l_binned'
    var3 = 'residuals'

    fig = plt.figure()
    ax = fig.add_subplot(projection='3d')
    ax.scatter(training_data[var1], training_data[var2], training_data[var3],
               c=training_data.surging, label=training_data.surging)

    plt.xlabel(var1)
    plt.ylabel(var2)

    plt.title('plotting vars in 3d')

    plt.show()


def plotResultsMap(year):

    results = gpd.read_file(f'results/Results.gpkg')
    results = results[results['year'] == year]
    surging = results[results['surging'] == 1]
    notsurging = results[results['surging'] == 0]
    nodata = results[results['surging'] == -999]
    training = results[results['training'] == 1]

    # plot
    #fig = plt.figure(1, (15, 15))
    ax = surging.plot(column='probability', cmap='Reds', label='surging', legend=False,
                      edgecolor='darkred', linewidth=0.5, figsize=(10, 15))

    #ax = surging.plot(label='surging', legend=False,
    #                  edgecolor='red', linewidth=1, figsize=(10, 15))

    notsurging.plot(ax=ax, column='probability', cmap='Blues', label='not surging', legend=False,
                    edgecolor='darkblue', linewidth=0.5)

    nodata.plot(ax=ax, color='grey', label='no data', legend=False, edgecolor='grey',
                linewidth=0.5)

    training.boundary.plot(ax=ax, color='white', label='training data',
                           linewidth=1)

    #notsurging.plot(ax=ax, label='not surging', legend=False,
    #                edgecolor='Blue', linewidth=1)

    #cubify.plot(ax=ax, cmap='Spectral_r')

    #cx.add_basemap(ax, crs=results.crs.to_string(), source=cx.providers.Esri.WorldImagery)
    cx.add_basemap(ax, crs=results.crs.to_string(), source=cx.providers.OpenStreetMap.Mapnik)

    #plt.xlim(550000, 850000)  # rozsah x-axis
    #plt.ylim(8800000, 9000000)  # rozsah y-axis

    # move text down
    txt = ax.texts[-1]
    txt.set_position([0.5, -0.1])
    txt.set_ha('center')
    txt.set_va('bottom')

    # remove x and yticks
    plt.xticks([])
    plt.yticks([])

    # title, legend, north arrow, scale
    plt.title(f"Svalbard Surges {year} \n (Probabilities)")

    # Create colorbars for the colormaps
    norm_surging = mcolors.Normalize(vmin=0, vmax=1)
    norm_notsurging = mcolors.Normalize(vmin=1, vmax=0)

    sm_surge = plt.cm.ScalarMappable(cmap='Reds', norm=norm_surging)
    sm_surge.set_array([])  # Only needed for the colorbar

    sm_notsurge = plt.cm.ScalarMappable(cmap='Blues', norm=norm_notsurging)
    sm_notsurge.set_array([])  # Only needed for the colorbar

    # Add colorbars to the plot
    cbar_surge = plt.colorbar(sm_surge, ax=ax, fraction=0.025, pad=0.04, location='right')
    cbar_surge.set_label('Surging Probability')

    cbar_notsurge = plt.colorbar(sm_notsurge, ax=ax, fraction=0.025, pad=0.04, location='right')
    cbar_notsurge.set_label('Not Surging Probability')

    # Position colorbars in the bottom right corner
    cbar_surge.ax.set_position([0.85, 0.525, 0.03, 0.25])  # [left, bottom, width, height]
    cbar_notsurge.ax.set_position([0.85, 0.225, 0.03, 0.25])  # [left, bottom, width, height]
    cbar_notsurge.ax.invert_yaxis()
    import matplotlib.font_manager as fm
    fontprops = fm.FontProperties(size=5)

    from mpl_toolkits.axes_grid1.anchored_artists import AnchoredSizeBar
    scalebar = AnchoredSizeBar(ax.transData,
                               10000, '10 km', 'lower right',
                               pad=0.1,
                               color='black',
                               frameon=False,
                               size_vertical=1,
                               fontproperties=fontprops)

    ax.add_artist(scalebar)

    x, y, arrow_length = 0.05, 0.95, 0.01
    ax.annotate('N', xy=(x, y), xytext=(x, y - arrow_length - 0.05),
                arrowprops=dict(facecolor='black', width=0.5, headwidth=1),
                ha='center', va='center', fontsize=4,
                xycoords=ax.transAxes)

    plt.savefig(f'figs/results{year}probs1.png')
    plt.close()
    #plt.show()

def plotResultsMaps():
    from vars import date

    plotResultsMap(2019)
    plotResultsMap(2020)
    plotResultsMap(2021)
    plotResultsMap(2022)
    plotResultsMap(2023)


def plotDHColored(glacier_id, year, dem_year):
    # plot the points for given year with a shp in the background colored by elevation change

    glacier_name = glacier_names[glacier_id]

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
    shp = gpd.read_file(f'temp/glaciers/{glacier_id}.gpkg')

    ax = shp.boundary.plot(color='black')
    ax.scatter(data.easting, data.northing, c=data.dh, cmap='Spectral_r')


    plt.legend()
    plt.xlabel('easting')
    plt.ylabel('northing')
    plt.title(f'Elevation differences between DEM ({dem_year}) and ICESat-2 heights ({year}) '
              f'\n {glacier_name}')
    plt.show()


def basicPointPlots(ax):
    # basic h/dh plot for every glacier/year
    from pathlib import Path
    import os

    features = gpd.read_file('temp/svalbard_features.gpkg')
    glacier_ids = list(features['glacier_id'].values)
    for glacier_id in glacier_ids:
        for year in [2019, 2020, 2021, 2022, 2023]:
            outpath = Path(f'eliskasieglova.github.io/imgs/{glacier_id}_{year}_{ax}.png')
            if outpath.is_file():
                continue
            try:
                data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
            except:
                continue
            plt.scatter(data.h_norm, data.dh, s=1.5, marker='.')
            plt.title(f'Elevation change on {glacier_names[glacier_id]} \n '
                      f'between DEM (2008-2012) and ICESat-2 measurements ({year})')
            plt.ylim(-100, 100)
            plt.xlabel('elevation (m)')
            plt.ylabel('elevation change (m)')
            plt.savefig(outpath)
            plt.close()


def didThisGlacierSurgeMap():
    features = gpd.read_file('temp/svalbard_features.gpkg')
    results = gpd.read_file('results/RFresults_svalbard_2024-07-15.gpkg')
    shp = gpd.read_file('data/SJM_adm0.shp')
    shp = shp.to_crs(32633)
    glacier_ids = list(features.glacier_id.values)
    surge_coefs = []
    probas = []
    for glacier_id in glacier_ids:
        subset = results[results['glacier_id'] == glacier_id]
        if len(subset) == 0:
            surge_coefs.append(-999)
            probas.append(1)
            continue
        max_surging = max(list(subset['surging'].values))  # returns 1 or 0
        if max_surging == 0:
            surge_coefs.append(0)
            probas.append(0)
        elif max_surging == -999:
            surge_coefs.append(-999)
            probas.append(-999)
        else:
            subset_surging = subset[subset['surging'] == 1]
            surge_coefs.append(1)
            probas.append(max(list(subset_surging['probability'].values)))
    # color the features
    features['surging'] = surge_coefs
    features['color'] = ['red' if x == 1 else 'blue' if x == 0 else 'grey' for x in features['surging'].values]
    features['probability'] = probas
    features['alpha'] = [0.5 if x < 0.75 else 1 for x in features['probability'].values]
    features.to_file('temp/surging_probas_total.gpkg')
    ax = features.plot(color=features['color'], alpha=features['alpha'])
    shp.boundary.plot(ax=ax, color='black')
    plt.title('Surging Glaciers')
    plt.xlim(300000, 950000)  # rozsah x-axis
    plt.ylim(8400000, 9050000)  # rozsah y-axis
    plt.show()


def plotATL06vsATL08(glacier_id, year):

    glacier_name = glacier_names[glacier_id]

    data = gpd.read_file(f'temp/glaciers/{glacier_id}_{year}.gpkg')
    shp = gpd.read_file(f'temp/glaciers/{glacier_id}.gpkg')
    atl06 = data[data['product'] == 'ATL06']
    atl08 = data[data['product'] == 'ATL08']

    ax = shp.boundary.plot(edgecolor='black', linewidth=1, label='glacier boundary')
    cx.add_basemap(ax, crs=shp.crs.to_string(), source=cx.providers.Esri.WorldImagery)

    txt = ax.texts[-1]
    txt.set_position([0.5, -1])
    txt.set_ha('center')
    txt.set_va('bottom')

    ax.set_axis_off()
    plt.axis('equal')

    ax.scatter(atl06.easting, atl06.northing, label='ATL06', s=1)
    ax.scatter(atl08.easting, atl08.northing, label='ATL08', s=1)

    plt.legend()
    plt.xlabel('easting')
    plt.ylabel('northing')
    plt.title(f'ATL06 vs ATL08 measurements \n {glacier_name} ({year})')

    plt.show()



