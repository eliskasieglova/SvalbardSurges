import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import svalbardsurges.analysis

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

def plot_hypso_curves(data, label):
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
    plt.subplots(2, 2, sharey=True, sharex=True)
    plt.suptitle(label, fontsize=16)

    n = 1
    for year in list(hypso_data)[:-1]:

        # plot hypsometric curve
        ax1 = plt.subplot(2, 2, n)
        ax1.plot(hypso_data[year]['abs'], hypso_data[year].index.mid)
        ax1.set_title(year)
        ax1.set_facecolor('aliceblue')

        # add stddev to plot
        ax1.text( 2, 2, f'std = {stddev[year].values}', fontsize='xx-small')

        # plot histogram
        ax2 = ax1.inset_axes([.65, .65, .3, .3], xticklabels=[])
        ax2.bar([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], hypso_data[year]['count'], width=0.4)
        n = n + 1

    plt.savefig(f'figures/{label}.png')
    #plt.show()

        # plot histogram


    return

