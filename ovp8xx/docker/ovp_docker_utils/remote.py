#%%
import hashlib
import logging
import os
import requests
import bz2
from pathlib import Path

from tqdm import tqdm

import ovp_docker_utils.logs

logger = logging.getLogger(__name__)

def compress_bz2(file_path):
    with open(file_path, 'rb') as input:
        with bz2.BZ2File(file_path+".bz2", 'wb') as output:
            pbar = tqdm(total=os.path.getsize(file_path), desc="Compressing", unit="chunks")
            while True:
                chunk = input.read(8192)
                if not chunk:
                    break
                output.write(chunk)
                pbar.update(len(chunk))

def uncompress_bz2(file_path: str, output:str=""):
    # uncompress
    if not output:
        output = file_path[:-4]
    with bz2.BZ2File(file_path, 'rb') as input:
        with open(output, 'wb') as output:
            pbar = tqdm(total=os.path.getsize(file_path), desc="Uncompressing", unit="chunks")
            while True:
                chunk = input.read(8192)
                if not chunk:
                    break
                output.write(chunk)
                pbar.update(len(chunk))
  
def get_hash(file_path):
    if Path(file_path).is_absolute():
        file_path = Path(file_path).as_posix()

    with open(file_path, 'rb') as f:
        bytes = f.read() # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest();
        return readable_hash

def download_file(url, destination):
    response = requests.get(url, stream=True)
    # with open(destination, 'wb') as out_file:
    #     shutil.copyfileobj(response.raw, out_file)
    import tqdm
    with open(destination, 'wb') as f:
        for chunk in tqdm.tqdm(response.iter_content(chunk_size=8192), desc="Downloading", unit="KB"):
            if chunk:
                f.write(chunk)
    del response
def download_if_unavailable(url, dl_path, sha_256=None, uncompress = True)->bool:
    download = True
    available = False
    # check if file exists
    if dl_path.endswith('.bz2'):
        uncompressed_path = dl_path[:-4]
    else:
        uncompress = False
        uncompressed_path = dl_path

    if os.path.exists(uncompressed_path):
        logger.info(f"File already exists: {uncompressed_path}")
        if sha_256:
            hash = get_hash(uncompressed_path)
            if hash == sha_256:
                logger.info(f"File hash matches: {uncompressed_path}")
                download = False
                available = True
            else:
                logger.warning(f"{uncompressed_path} hash does not match specified: {hash}")
        else:
            logger.info("No hash provided for new file, skipping download.")
            logger.info(f"File hash: {get_hash(uncompressed_path)}")
            download = False
    else:
        logger.info(f"{uncompressed_path} does not exist.")

    if download:
        logger.info(f"Attempting download.")
        download_file(url, dl_path)
        if uncompress:
            uncompress_bz2(dl_path,uncompressed_path)
            hash = get_hash(uncompressed_path)
            logger.info(f"Downloaded file hash: {uncompressed_path}")
            if hash == sha_256:
                logger.info(f"Downloaded file hash matches: {uncompressed_path}")
                available = True
            else:
                logger.info(f"Downloaded file hash does not match specified hash")
    return uncompressed_path

tmp_dir = Path(__file__).parent / "tmp"
def hash_and_compress(fname:str):
    file_path = (tmp_dir/fname).as_posix()
    logger.info(f'{file_path} sha256 hash: {get_hash(file_path)}')
    logger.info(f"Compressing...")
    compress_bz2(file_path)

if __name__ == "__main__":
    url = "https://www.dropbox.com/scl/fi/b5wl1zvub01eebl4ro2ja/l4t-ifm3dlab.0.0.0-arm64.tar.bz2?rlkey=auzdlol02xrpnupcfp1fzzre9&st=pmdwe4ne&dl=0".replace("www.dropbox.com", "dl.dropboxusercontent.com")
    fname = (tmp_dir/"l4t-ifm3dlab.0.0.0-arm64.tar").as_posix()
    destination = fname + '.bz2'
    sha_256 = "c322e9d5e0b0841c58b15e879aee725f1180dd365434a0034afb0e602a62e69d"

    import sys
    if "ipython" in sys.modules:
        print("Running in IPython")
        #%%
        download_and_uncompress(url, destination, sha_256)
        #%%
        hash_and_compress(r"C:\Users\usdagest\dev\ifm3d-examples\ovp8xx\docker\ovp_docker_utils\l4t-ifm3dlab.0.0.0.arm64.tar")
        #%%
    else:
        ...
        #%%
        import typer
        typer.run(hash_and_compress)