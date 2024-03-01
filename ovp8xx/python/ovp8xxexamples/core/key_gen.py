#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
from pathlib import Path
import datetime
import os
import argparse

import ifm3dpy

try:
    import paramiko
except ImportError:
    paramiko_available = False


def assign_key(ip, key_title, key_size, target_dir):

    private_key_path = Path(target_dir) / key_title
    public_key_path = Path(target_dir) / f"{key_title}.pub"

    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
    elif not os.path.isdir(target_dir):
        raise ValueError(f"{target_dir} exists but is not a directory")

    keys_exist = private_key_path.exists() or public_key_path.exists()

    o3r = ifm3dpy.O3R(ip)

    if not keys_exist:

        if not paramiko_available:
            raise ImportError(
                "paramiko is not available, cannot generate keys")

        comments = f"Key generated for ifm ovp8xx ssh access {datetime.datetime.now()}"

        key = paramiko.RSAKey.generate(bits=key_size)

        public_key_signature = f"ssh-rsa {key.get_base64()} {comments}"
        o3r.set({"device": {"network": {"authorized_keys": public_key_signature}}})

        # save keypair
        key.write_private_key_file(str(private_key_path))
        with open(ssh_dir / f"{key_title}.pub", "w") as f:
            f.write(public_key_signature)

    if paramiko_available:

        print(f"Connecting to {o3r.ip} to verify the keys are set correctly.")

        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(o3r.ip, username="oem", key_filename=str(private_key_path))
        stdin, stdout, stderr = ssh.exec_command("docker ps -a")

        print(stdout.read().decode())


if __name__ == "__main__":

    user_dir = Path("~").expanduser()
    ssh_dir = user_dir / ".ssh"

    parser = argparse.ArgumentParser(
        description="ifm ods example",
    )
    parser.add_argument(
        "--IP", type=str, default=os.environ.get("IFM3D_IP", "192.168.0.69"), help="IP address to be used"
    )
    parser.add_argument(
        "--key_title", type=str, default="id_rsa_ovp8xx", help="Title of the key"
    )
    parser.add_argument(
        "--key_size", type=int, default=4096, help="Size of the key"
    )
    parser.add_argument(
        "--target_dir", type=str, default=str(ssh_dir), help="Directory to save the key"
    )
    args = parser.parse_args()
    assign_key(args.IP, args.key_title, args.key_size, args.target_dir)
