import matplotlib.pyplot as plt

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

def plot_hypso_curves(data):
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

    # initialize subplots and n value for visualization
    plt.subplots(2, 2, sharey=True, sharex=True)
    plt.tight_layout()
    n = 1

    for year in list(data)[:-1]:
        plt.subplot(2, 2, n)
        plt.title(year)
        plt.plot(data[year]['abs'], data[year].index.mid)

        n=n+1

    plt.show()

    return
