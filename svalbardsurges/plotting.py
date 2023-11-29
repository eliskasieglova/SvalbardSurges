import matplotlib.pyplot as plt
import xarray as xr
import warnings
# Catch a deprecation warning that arises from skgstat when importing xDEM
with warnings.catch_warnings():
    import numba
    warnings.simplefilter("ignore", numba.NumbaDeprecationWarning)
    import xdem


def plotHypso(data, glacier_id, glacier_name, glacier_area, output_path, pltshow, pltsave):
    """
    Plot hypsometric curves.

    Parameters
    ----------
    -data
        Dictionary of pd dataframes of yearly binned elevation changes.
    -glacier_id
        glacier id for plot title and naming figure
    glacier_name
        glacier name for plot title and naming figure
    glacier_area
        glacier area in km2 for creating histogram (points per square kilometer)

     Results
     -------
     Saved figure of hypsometric curves and histograms for each year in dataset.
    """

    if pltshow | pltsave:
        # initialize subplots and n value for visualization
        plt.subplots(2, 3, sharey=True, sharex=True)
        plt.suptitle(f'{glacier_name} ({glacier_id})', fontsize=16)

        n = 1
        for year in list(data):
            # plot histogram
            ax1 = plt.subplot(2, 3, n)
            ax1.barh(y = data[year].index.mid,
                     width = data[year]['count'],
                     height = data[year].index.right - data[year].index.left,
                     edgecolor="black", zorder=0, alpha=0.1
                    )
            #ax1.set_xlim(0,3)

            # plot hypsometric curve
            ax2 = ax1.twiny()
            ax2.plot(data[year]['value'], data[year].index.mid, zorder=100)
            ax2.set_title(f"2010-{year}")
            ax2.set_facecolor('aliceblue')
            ax2.set_xlim(-30, 60)

            n = n + 1

    plt.tight_layout()

    # if pltshow -> show plot, if pltsave -> save plot
    if pltshow:
        plt.show()

    if pltsave:
        plt.savefig(output_path)

    plt.close()

    return

def plotEvaluatedHypso(hypso, pltshow, pltsave):
    # todo





    return


def plot_yearly_dh(data_path, glacier_outline, glacier_name, glacier_id, output_path, pltshow, pltsave):
    """
    Plot DH of IS2 and DEM on map.

    Parameters:
    ----------
    -data

    -glacier_outline
        shapefile of glacier
    -glacier_name
        glacier name for plotting and saving figure
    - glacier_id
        glacier id for plotting and saving figure
    - output_path

    Returns:
    -------
    Saves figure of plotted yearly elevation differences.
    """
    pltshow=False

    if pltsave | pltshow:
        # open data
        data = xr.open_dataset(data_path)

        # initialize figure with subplots
        fig = plt.figure(figsize=(8, 5))
        fig.subplots(1, 5, sharey=True)
        plt.suptitle(f'{glacier_name} ({glacier_id})', fontsize=16)


        # todo adapt for hydrological years
        n = 1

        day = 1031
        years = [2018, 2019, 2020, 2021, 2022]

        for year in years:
            y = year * 10000
            hydrosilvestr = y + day

            subset = data.where(())

            plt.subplot(1, 5, n)
            plt.title(f"2010 - {year}")

            # plot polygon of glacier outline
            polygon = glacier_outline.iloc[0]["geometry"]
            if "Multi" not in polygon.geom_type:
                polygons = [polygon]
            else:
                polygons = polygon.geoms

            for polygon in polygons:
                plt.plot(*polygon.exterior.xy, color='black')

            # scatterplot todo
            im = plt.scatter(subset.easting, subset.northing, c=subset.dh, cmap='seismic_r', vmin=-40, vmax=40)
            plt.axis('off')
            plt.gca().set_aspect('equal')

            n = n + 1

        fig.subplots_adjust(right=0.8)
        cbar_ax = fig.add_axes([0.86, 0.15, 0.05, 0.7])
        fig.colorbar(im, cax=cbar_ax)

    # if pltshow -> show plot, if pltsave -> save as figure
    if pltshow:
        plt.show()

    if pltsave:
        plt.savefig(output_path)

    plt.close()

    return


def plot_is2(data):

    fig = plt.figure()

    im = plt.scatter(data.easting, data.northing, c=data.dh, cmap='seismic', vmin=-40, vmax=40)
    plt.gca().set_aspect('equal')
    cbar_ax = fig.add_axes([0.86, 0.15, 0.05, 0.7])
    fig.colorbar(im, cax=cbar_ax)

    # filter out nan
    is2 = data.where(data.dem_elevation < 2000).dropna(dim='index')

    return is2


def plot_hypso_arcticdem(data, glacier_id, glacier_name, glacier_area, output_path, pltshow, pltsave):
    """
    Plot hypsometric curves from ArcticDEM data.

    Parameters
    ----------
    -data
        Dictionary of pd dataframes of yearly binned elevation changes.
    -glacier_id
        glacier id for plot title and naming figure
    glacier_name
        glacier name for plot title and naming figure
    glacier_area
        glacier area in km2 for creating histogram (points per square kilometer)

     Results
     -------
     Saved figure of hypsometric curves and histograms for each year in dataset.
    """

    if pltsave | pltshow:

        # initialize subplots and n value for visualization
        plt.subplots(2, 3, sharey=True, sharex=True)
        plt.suptitle(f'{glacier_name} ({glacier_id}) - ArcticDEM', fontsize=16)

        n = 1
        for year in list(data):
            # plot histogram
            ax1 = plt.subplot(2, 3, n)
            ax1.barh(y = data[year].index.mid,
                     width = data[year]['count']/glacier_area,
                     height = data[year].index.right - data[year].index.left,
                     edgecolor="black",
                     zorder=0,
                     alpha=0.1
                 )
            ax1.set_xlim(0,1000)

            # plot hypsometric curve
            ax2 = ax1.twiny()
            ax2.plot(data[year]['value'], data[year].index.mid)
            ax2.set_title(f"2010-{year}")
            ax2.set_facecolor('aliceblue')
            ax2.set_xlim(-40, 40)

            n = n + 1

        plt.tight_layout()

    if pltshow:
        plt.show()

    if pltsave:
        plt.savefig(output_path)

    plt.close()

    return


def plot_arcticDEM_dh(data, ref_dem_path, year, glacier_outline, glacier_name, glacier_id, output_path, pltshow, pltsave):
    '''
    Plot ArcticDEM difference compared to reference year (2010).

    Parameters:
    -----------
    - data
        dictionary of paths to cropped ArcticDEMs
    - year
        determined by for-loop which loops through available years
    - glacier_outline
        shapefile of glacier outline to be plotted
    - output_path
        path where output figure should be saved
    - pltshow
        boolean
    - pltsave
        boolean

    Returns:
    --------
    Saves figure of map of glacier elevation changes from ArcticDEM for each available year.
    '''

    if pltshow | pltsave:
        # load data
        ref_dem = xdem.DEM(ref_dem_path)
        arcticdem = xdem.DEM(data[year]).reproject(ref_dem)

        # create difference DEM
        d_dem = arcticdem - ref_dem

        # initiate plot
        plt.figure()
        plt.title(f'{glacier_name}({glacier_id}), 2010-{year}, ArcticDEM')

        # plot shapefile (glacier outline)
        polygon = glacier_outline.iloc[0]["geometry"]
        if "Multi" not in polygon.geom_type:
            polygons = [polygon]
        else:
            polygons = polygon.geoms

        for polygon in polygons:
            plt.plot(*polygon.exterior.xy, color='black')

        # plot difference DEM
        d_dem.show(vmin=-50, vmax=50, cmap='seismic_r')

    # action based on preferences
    if pltshow:
        plt.title(f'{glacier_name} ArcticDEM')
        plt.show()

    if pltsave:
        plt.savefig(output_path)

    plt.close()

    return


def plotSurges(svalbard_shp, results_df, pltshow, pltsave):


    plt.figure()


    # initiate plot
    # plot svalbard

    # plot points where surge (color by year)
    for i, row in results_df.iterrows():
        # if one of the years indicates a glacier surge
        if type(results_df['surge'][i]) != float:

            if (1 in results_df['surge'][i]) | (2 in results_df['surge'][i]):
                print(f"{results_df['glacier_name'][i]} is surging!")

                # plot glacier outline
                polygon = results_df["geom"][i]
                if "Multi" not in polygon.geom_type:
                    polygons = [polygon]
                else:
                    polygons = polygon.geoms

                for polygon in polygons:
                    plt.plot(*polygon.exterior.xy, color='red')

                print()

    plt.gca().set_aspect('equal')
    plt.title(f'surging glaciers')
    plt.show()

    return
