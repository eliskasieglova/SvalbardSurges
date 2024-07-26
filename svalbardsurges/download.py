import icepyx as ipx
from pathlib import Path
from vars import label, spatial_extent, date_range
from vars import products
import management


def downloadSvalbard():

    for product in products:

        print(product)

        download_icesat(
            data_product=product,
            spatial_extent=spatial_extent,
            date_range=date_range
        )

    return


def download_icesat(data_product, spatial_extent, date_range):
    """
    Download ICESat-2 data from earthdata.

    Reccomendation: have earthdata login details stored as environment variables (EARTHDATA_USERNAME, EARTHDATA_PASSWORD)

    Params
    ------
    - spatial_extent
        bounding box of wanted area as list of coords [left, bottom, right, top] in decimal degrees
    - date_range
        list of beginning and end of time span ['yyyy-mm-dd', 'yyyy-mm-dd']
    - data_product
        'ATL03/6/8' as str.

    Return
    ------
    Output path to ICESat-2 data product.
    """

    # granules are saved to cache
    output_path = Path(f'data/raw/{data_product}')
    management.createFolder(output_path)

    # specifications for download
    region_a = ipx.Query(
        data_product,
        spatial_extent,
        date_range,
        start_time='00:00:00',
        end_time='23:59:59'
    )

    region_a.avail_granules()

    print('ordering granules')
    # order and download granules, save them
    region_a.order_granules()
    print(f'downloading granules {data_product}')
    region_a.download_granules(output_path)

    return output_path
