import tempfile
import shutil
import os
from pathlib import Path
import requests

def download():

    # cache path
    cache_path = Path("cache/")

    # labels for downloaded data
    dem_label = Path('dem.tif')
    gao_label = Path('is2.nc')

    # download URLs
    dem_name = 'NP_S0_DTM5_2011_25163_33' # region of Scheelebreen
    dem_url = f'https://public.data.npolar.no/kartdata/S0_Terrengmodell/Delmodell/{dem_name}.zip'
    gao_url = 'https://api.npolar.no/dataset/f6afca5c-6c95-4345-9e52-cfe2f24c7078/_file/3df9512e5a73841b1a23c38cf4e815e3'

    dem = download_file(dem_url, dem_label)
    gao = download_file(gao_url, gao_label)

    print(dem)
    print(gao)

def download_file(url: str, filename: str | None = None, directory: Path | str | None = None) -> Path:
    """
    Download a file from the requested URL.

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

download()

