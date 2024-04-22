#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
# FW >= 1.4.X require key authentication to connect to the VPU via SSH
# This script generates a key pair and assigns the public key to the device
# The private key is saved in the user's .ssh directory
# The script also optionally tests the private key by connecting to the device and running an echo command


from pathlib import Path
from datetime import datetime
import os
import argparse
import logging

from ifm3dpy.device import O3R

logger = logging.getLogger(__name__)

try:
    import paramiko
    paramiko_available = True
except ImportError:
    paramiko_available = False
    raise RuntimeError("import paramiko failed!")

DEFAULT_KEY_TITLE = "id_rsa_ovp8xx"
DEFAULT_KEY_SIZE = 4096

USER_DIR = Path("~").expanduser()
SSH_DIR = USER_DIR / ".ssh"

def _setup_logging(args):
    logPath = "./logs"  
    if not os.path.exists("./logs"):
        os.makedirs("./logs")
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    fileName = f"ssh_key_gen_{current_datetime}.log"
    logger.setLevel(logging.INFO)
    logFormatter = logging.Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s")
    fileHandler = logging.FileHandler("{0}/{1}.log".format(logPath, fileName))
    fileHandler.setFormatter(logFormatter)
    consoleHandler = logging.StreamHandler()
    consoleHandler.setFormatter(logFormatter)
    logger.addHandler(fileHandler)
    logger.addHandler(consoleHandler)
    return logger


def assign_key(ip: str, key_title: str = DEFAULT_KEY_TITLE, key_size=DEFAULT_KEY_SIZE, target_dir=SSH_DIR) -> str:
    """
    Assigns a key to the device

    Parameters
    ----------
    ip : str
        IP address of the device
    key_title : str, optional
        Title of the key, by default "id_rsa_ovp8xx"
    key_size : int, optional
        Size of the key, by default 4096
    target_dir : str, optional
        Directory to save the key, by default "~/.ssh"   
    """

    target_dir = Path(target_dir).expanduser()
    private_key_path = Path(target_dir) / key_title
    public_key_path = Path(target_dir) / f"{key_title}.pub"

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    elif not os.path.isdir(target_dir):
        raise ValueError(f"{target_dir} exists but is not a directory")

    keys_exist = private_key_path.exists() and public_key_path.exists()

    o3r = O3R(ip)

    if private_key_path.exists() and public_key_path.exists():

        with open(public_key_path, "r") as f:
            public_key_signature = f.read()

    else:

        comments = f"Key generated for ifm ovp8xx ssh access {datetime.now()}"

        if private_key_path.exists():

            key = paramiko.RSAKey(filename=private_key_path.as_posix())

        else:

            if not paramiko_available:
                raise ImportError(
                    "paramiko is not available, cannot generate keys")

            key = paramiko.RSAKey.generate(bits=key_size)
            key.write_private_key_file(private_key_path.as_posix())

        public_key_signature = f"ssh-rsa {key.get_base64()} {comments}"
        with open(public_key_path.as_posix(), "w") as f:
            f.write(public_key_signature)

    o3r.set({"device": {"network": {"authorized_keys": public_key_signature}}})

    return private_key_path.as_posix()


def test_key(ip, private_key_path):

    o3r = O3R(ip)
    if paramiko_available:
        logger.info(f"Connecting to {o3r.ip} to verify the keys are set correctly.")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(o3r.ip, username="oem", key_filename=str(private_key_path))
        stdin, stdout, stderr = ssh.exec_command(
            "echo 'Hello, world! (echoed back from the device)'")

        logger.info(stdout.read().decode())


if __name__ == "__main__":

    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        O3R_IP = config.IP

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the examples configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("falling back to ssh_key_gen default configuration.")
        O3R_IP = os.environ.get("IFM3D_IP", "192.168.0.69")

    parser = argparse.ArgumentParser(
        description="ssh key generator script for OVP8xx",
    )
    parser.add_argument(
        "--IP", type=str, default=O3R_IP, help="IP address to be used"
    )
    parser.add_argument(
        "--key_title", type=str, default="id_rsa_ovp8xx", help="Title of the key"
    )
    parser.add_argument(
        "--key_size", type=int, default=4096, help="Size of the key"
    )
    parser.add_argument(
        "--target_dir", type=str, default=str(SSH_DIR), help="Directory to save the key"
    )
    parser.add_argument(
        "--log-file",
        help="The file to save relevant output",
        type=Path,
        required=False,
        default=Path("deleted_configurations.log"),
        dest="log_file",
    )

    args = parser.parse_args()

    # register a stream and file handler for all logging messages
    logger = _setup_logging(args=args)

    private_key_path = assign_key(
        args.IP, args.key_title, args.key_size, args.target_dir)
    test_key(args.IP, private_key_path)
