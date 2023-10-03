import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import svalbardsurges.analysis
import os

def plot_pts(data, var):
    """
    Creates a scatter plot of input data.

    Works only for IS2 data as the input into the scatter plot are according to IS2 structure
    (x=data.easting, y=data.northing.

    Parameters
    ----------
    - data
        data to plot (IS2 data)
    - var
        which variable to plot (name of variable as string)
    """

    plt.scatter(data.easting, data.northing, c=data[var])
    plt.gca().set_aspect('equal')
    plt.show()

def plot_hypso_curves(data, label, glacier_outline):
    """
    Create a plot of binned hypsometric curves.

    Parameters
    ----------
    -data
        Dictionary of pd dataframes of yearly binned elevation changes.

     Results
     -------
     Plot of hypsometric curves for each year in dataset.
    """

    # create dataset of hypsometrically binned data
    hypso_data, stddev = svalbardsurges.analysis.hypsometric_binning(data)

    # initialize subplots and n value for visualization
    plt.subplots(2, 2, sharey=True)
    plt.suptitle(f'{glacier_outline.NAME.iloc[0]} ({label})', fontsize=16)

    area = glacier_outline.geometry.area.iloc[0] / 1e6

    n = 1
    for year in list(hypso_data)[:-1]:
        # plot histogram
        ax1 = plt.subplot(2, 2, n)
        ax1.barh(y = hypso_data[year].index.mid,
                 width = hypso_data[year]['count']/area,
                 height = hypso_data[year].index.right - hypso_data[year].index.left,
                 edgecolor="black",
                 zorder=0,
                 alpha=0.1
             )
        ax1.set_xlim(0,1)

        # plot hypsometric curve
        ax2 = ax1.twiny()
        ax2.plot(hypso_data[year]['abs'], hypso_data[year].index.mid, zorder=100)
        ax2.set_title(year)
        ax2.set_facecolor('aliceblue')
        ax2.set_xlim(-30, 30)

        n = n + 1

        # add stddev to plot
        #ax1.text( 2, 2, f'std = {stddev[year].values}', fontsize='xx-small')

    plt.tight_layout()

    # create directory for figures if does not exist
    if not os.path.isdir("figures/"):
        os.mkdir("figures/")

    # save figure
    #plt.savefig(f'figures/{label}.png')

    return


def plot_yearly_dh(data, label, glacier_outline):
    # plot elevation change on glacier

    min_dh = min(data.dh.values)
    max_dh = max(data.dh.values)

    fig, axes = plt.subplots(1, 4, sharey=True)
    plt.suptitle(f'{glacier_outline.NAME.iloc[0]} ({label})', fontsize=16)

    n = 1

    for year, data_subset in data.groupby(data["date"].dt.year):
        if year != 2022:

            plt.subplot(1, 4, n)
            plt.title(year)
            polygon = glacier_outline.iloc[0]["geometry"]
            if "Multi" not in polygon.geom_type:
                polygons = [polygon]
            else:
                polygons = polygon.geoms

            for polygon in polygons:
                plt.plot(*polygon.exterior.xy, color='black')

            im = plt.scatter(data_subset.easting, data_subset.northing, c=data_subset.dh + 31.55, cmap='seismic', vmin=-50, vmax=50)
            plt.axis('off')
            plt.gca().set_aspect('equal')

            n = n+1

    fig.subplots_adjust(right=0.8)
    cbar_ax = fig.add_axes([0.86, 0.15, 0.05, 0.7])
    fig.colorbar(im, cax=cbar_ax)
    plt.show()


    # scatterplot of available data points that we have
    # scatter = plt.scatter(data.easting, data.northing, c=data["date"].dt.year, cmap='hsv', s=0.5)
    # plt.title(year)
    # legend1 = plt.legend(*scatter.legend_elements(), loc="upper left", title="Classes")
    # plt.show()


    return
