#%%
import hashlib
import logging
import os
import requests
import bz2
from shutil import copyfileobj

from tqdm import tqdm

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def compress(file_path):
    with open(file_path, 'rb') as input:
        with bz2.BZ2File(file_path+".bz2", 'wb') as output:
            pbar = tqdm(total=os.path.getsize(file_path), desc="Compressing", unit="chunks")
            while True:
                chunk = input.read(8192)
                if not chunk:
                    break
                output.write(chunk)
                pbar.update(len(chunk))

def uncompress_bz2(file_path):
    # uncompress
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
def download_if_unavailable(url, destination, sha_256=None)->bool:
    download = True
    available = False
    # check if file exists
    if os.path.exists(destination):
        logger.info(f"File already exists: {destination}")
        if sha_256:
            hash = get_hash(destination)
            if hash == sha_256:
                logger.info(f"File hash matches: {destination}")
                download = False
                available = True
            else:
                logger.warning(f"{destination} hash does not match specified: {hash}")
        else:
            logger.info("No hash provided for new file, skipping download.")
            logger.info(f"File hash: {get_hash(destination)}")
            download = False
    else:
        logger.info(f"{destination} does not exist.")

    if download:
        logger.info(f"Attempting download.")
        download_file(url, destination)
        hash = get_hash(destination)
        logger.info(f"Downloaded file hash: {hash}")
        if hash == sha_256:
            logger.info(f"Downloaded file hash matches: {destination}")
            available = True
        else:
            logger.info(f"Downloaded file hash does not match specified hash")
            os.remove(destination)
            logger.info(f"Deleted: {destination}")
    return available

if __name__ == "__main__":
    ...
    #%%
    url = "https://www.dropbox.com/scl/fi/xioc7bczqen6z9285sdog/ifm3dlab_0.0.0-arm64.tar.bz2?rlkey=70anev2iqc71i3eapi93utpqg&st=gerd3yom&dl=0".replace("www.dropbox.com", "dl.dropboxusercontent.com")
    fname = "ifm3dlab_0.0.0-arm64.tar"
    destination = fname + '.bz2'
    sha_256 = "5b5a817332d9ac05a905910f3d5260ab15b0a22d58a792a177ba6ac58d28ce01"

    download_if_unavailable(url, destination, sha_256)
    if destination.endswith('.bz2'):
        uncompress_bz2(destination)

    #%%