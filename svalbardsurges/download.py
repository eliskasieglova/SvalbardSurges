import tempfile
import shutil
import os
from pathlib import Path
import requests
import icepyx as ipx
from matplotlib import pyplot as plt


def download_file(url: str, filename: str | None = None, directory: Path | str | None = None) -> Path:
    """
    Download a file from the requested URL.
    Function from Erik.

    Parameters
    ----------
    - url:
        The URL to download the file from.
    - filename:
        The output filename of the file. Defaults to the basename of the URL.
    - directory:
        The directory to save the file in. Defaults to `cache/`

    Returns
    -------
    A path to the downloaded file.
    """

    # If `directory` is defined, make sure it's a path. If it's not defined, default to `cache/`
    if isinstance(directory, (str, Path)):
        out_dir = Path(directory)
    else:
        out_dir = Path("cache/")

    if filename is not None:
        out_path = out_dir.joinpath(filename)
    else:
        out_path = out_dir.joinpath(os.path.basename(url))

    # If the file already exists, skip downloading it.
    if not out_path.is_file():
        # Open a data stream from the URL. This means not everything has to be kept in memory.
        with requests.get(url, stream=True) as request:
            # Stop and raise an exception if there's a problem.
            request.raise_for_status()

            # Save the file to a temporary directory first. The file is constantly appended to due to the streaming
            # Therefore, if the stream is cancelled, the file is not complete and should be dropped.
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir).joinpath("temp.file")
                # Write the data stream as it's received
                with open(temp_path, "wb") as outfile:
                    shutil.copyfileobj(request.raw, outfile)

                # When the download is done, move the file to its ultimate location.
                shutil.move(temp_path, out_path)

    return out_path

def download_icesat(spatial_extent, date_range, data_product):
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
    output_path = Path(f'cache/is2_{data_product}')

    # if data is already downloaded don't run this function
    if output_path.is_dir():
        return output_path

    # specifications for download
    region_a = ipx.Query(
        data_product,
        spatial_extent,
        date_range,
        start_time='00:00:00',
        end_time='23:59:59'
    )

    region_a.avail_granules()
    region_a.granules.avail

    # login to earthdata
    region_a.earthdata_login()  # EARTHDATA_USERNAME and EARTHDATA_PASSWORD as environment variables

    # order and download granules, save them to cache/is2_{dataproduct}
    region_a.order_granules(subset=False)
    region_a.download_granules(output_path)

    return output_path



