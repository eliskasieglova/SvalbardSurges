import matplotlib.pyplot as plt
import xarray as xr

def plot_hypso_curves(data, glacier_id, glacier_name, glacier_area, output_path):
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

    if output_path.is_file():
        return

    # initialize subplots and n value for visualization
    plt.subplots(2, 2, sharey=True, sharex=True)
    plt.suptitle(f'{glacier_name} ({glacier_id})', fontsize=16)

    n = 1
    for year in list(data)[:-1]:
        # plot histogram
        ax1 = plt.subplot(2, 2, n)
        ax1.barh(y = data[year].index.mid,
                 width = data[year]['count']/glacier_area,
                 height = data[year].index.right - data[year].index.left,
                 edgecolor="black",
                 zorder=0,
                 alpha=0.1
             )
        ax1.set_xlim(0,3)

        # plot hypsometric curve
        ax2 = ax1.twiny()
        ax2.plot(data[year]['value'], data[year].index.mid, zorder=100)
        ax2.set_title(f"2010-{year + 1}")
        ax2.set_facecolor('aliceblue')
        ax2.set_xlim(-30, 30)

        n = n + 1

    plt.tight_layout()

    # save figure
    plt.savefig(output_path)
    plt.close()

    return

def plot_yearly_dh(data_path, glacier_outline, glacier_name, glacier_id, output_path):
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

    if output_path.is_file():
        return

    data = xr.open_dataset(data_path)

    fig = plt.figure(figsize=(8, 5))
    fig.subplots(1, 5, sharey=True)
    plt.suptitle(f'{glacier_name} ({glacier_id})', fontsize=16)

    n = 1

    for year, data_subset in data.groupby(data["date"].dt.year):

        plt.subplot(1, 5, n)
        plt.title(f"2010 - {year}")
        polygon = glacier_outline.iloc[0]["geometry"]
        if "Multi" not in polygon.geom_type:
            polygons = [polygon]
        else:
            polygons = polygon.geoms

        for polygon in polygons:
            plt.plot(*polygon.exterior.xy, color='black')

        im = plt.scatter(data_subset.easting, data_subset.northing, c=data_subset.dh, cmap='seismic_r', vmin=-40, vmax=40)
        plt.axis('off')
        plt.gca().set_aspect('equal')

        n = n + 1

    fig.subplots_adjust(right=0.8)
    cbar_ax = fig.add_axes([0.86, 0.15, 0.05, 0.7])
    fig.colorbar(im, cax=cbar_ax)
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
    #is2 = data.dropna(dim='index')

    return is2