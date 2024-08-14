#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import logging
import os
import sys
from pathlib import Path
from typing import Tuple, List

from paramiko import AutoAddPolicy
from paramiko.client import SSHClient
from scp import SCPClient


from .defaults import DEFAULT_IP

USING_IPYTHON = "ipykernel" in sys.modules
if USING_IPYTHON:
    logger = logging.getLogger("notebook")
else:
    logger = logging.getLogger("deploy")


def expand_pc_path(pc_path: str) -> str:
    if str(pc_path).startswith("~"):
        pc_path = Path().home().as_posix()+"/"+Path(pc_path).as_posix()[2:]
    pc_path = pc_path.replace(
        "./", str(Path(os.getcwd()))+"/").replace("\\", "/")
    return pc_path


def expand_remote_path(vpu_path: str, home = "/home/oem") -> str:
    vpu_path = str(vpu_path).replace("~", home)
    return vpu_path


def SSH_collect_OVP_handles(oem_username: str = "oem", password: str = "oem", private_key_path: str = None, IP: str = DEFAULT_IP, port: int = 22, remove_known_host: bool = True) -> Tuple[SSHClient, SCPClient]:
    """
    This function collects the ssh and scp handles for the vpu

    Parameters
    ----------
    oem_username : str, optional
        By default "oem"
    password : str, optional
        By default "oem"
    IP : str, optional
        By default "192.168.0.69"
    port : int, optional
        By default 22
    remove_known_hosts : bool, optionally remove the entry for this IP from the known_hosts file after connecting (useful when simultaneously sshing into system via cli),
        By default True

    Returns
    -------
    tuple[SSHClient, SCPClient]
        ssh and scp handles for the vpu

    Raises
    ------
    Exception
        If the vpu cannot be connected to
    """

    logging.getLogger("paramiko").setLevel(logging.INFO)
    logging.getLogger("scp").setLevel(logging.INFO)

    ssh: SSHClient = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())

    try:
        ssh.connect(hostname=IP, username=oem_username,
                    password=password, key_filename=private_key_path, timeout=1, port=port)
    except Exception as FailureToConnectError:
        if "timed out" in str(FailureToConnectError):
            logger.info(
                f"Attempt to connect to {oem_username}@{IP}:{port} timed out.")
        raise FailureToConnectError

    scp = SCPClient(ssh.get_transport())

    known_hosts_path = Path("~/.ssh/known_hosts").expanduser()
    if remove_known_host and known_hosts_path.exists():
        with open(known_hosts_path, "r") as f:
            lines = f.readlines()
        with open(known_hosts_path, "w") as f:
            f.write(
                "\n".join([line for line in lines if not (line.split(" ")[0] == IP)]))

    return ssh, scp


def SSH_listdir(ssh: SSHClient, path: str = "~") -> List[str]:
    """
    This function lists the contents of a directory via SSH

    Parameters
    ----------
    ssh : SSHClient
        ssh library native handle
    path : str, optional
        path to check, by default "~"

    Returns
    -------
    bool
        list of contents of the directory
    """
    cmd = f"ls {path}"
    _stdin, _stdout, _stderr = ssh.exec_command(cmd)
    return _stdout.read().decode().strip().split("\n")


def SSH_path_exists(ssh: SSHClient, path: str = "~") -> bool:
    """
    This function checks whether a path exists

    Parameters
    ----------
    ssh : SSHClient
        ssh library native handle
    path : str, optional
        path to check, by default "~"

    Returns
    -------
    bool
        Whether the path exists
    """
    cmd = f"cd {path}"
    _stdin, _stdout, _stderr = ssh.exec_command(cmd)
    if _stderr.read():
        tokenized_path = path.split("/")
        if len(tokenized_path) > 1:
            contents_of_parent = SSH_listdir(
                ssh, "/".join(tokenized_path[:-1]))
            path_exists = tokenized_path[-1] in contents_of_parent
        else:
            path_exists = False
    else:
        path_exists = True
    return path_exists


def SSH_isdir(ssh: SSHClient, path: str = "~") -> bool:
    """
    This function checks whether a path exists and is a directory

    Parameters
    ----------
    ssh : SSHClient
        ssh library native handle
    path : str, optional
        path to check, by default "~"

    Returns
    -------
    bool
        Whether the path exists and is a directory
    """
    cmd = f"cd {path}"
    _stdin, _stdout, _stderr = ssh.exec_command(cmd)
    return not bool(_stderr.read().decode())


def SSH_makedirs(ssh: SSHClient, path: str = "") -> None:
    """
    This function makes directories via SSH

    Parameters
    ----------
    ssh : SSHClient
        ssh library native handle
    path : str, optional
        path to check, by default ""

    Raises
    ------
    Exception
        If the path or one of its parents exists but is not a directory
    """
    sub_path_to_check = []
    if path[-1] != "/":
        path += "/"
    for dir in path.split("/"):
        if sub_path_to_check:
            sub_path = "/".join(sub_path_to_check)
            if not SSH_isdir(ssh, sub_path):
                if SSH_path_exists(ssh, sub_path):
                    logger.exception(
                        f"Error making directories, {path}, via SSH. {sub_path} is not a directory")
                    raise Exception(
                        f"Error making directories, {path}, via SSH. {sub_path} is not a directory")
                else:
                    _stdin, _stdout, _stderr = ssh.exec_command(
                        f"mkdir {sub_path}")
        sub_path_to_check += [dir]


def SCP_transfer_item(ssh: SSHClient, scp: SCPClient, src: str, dst: str, src_is_local: bool = True) -> None:
    """
    This function transfers a file or directory between the local machine and the vpu

    Parameters
    ----------
    ssh : SSHClient
        ssh library native handle
    scp : SCPClient
        scp library native handle
    src : str
        path to source file or directory
    dst : str
        path to destination file or directory
    src_is_local : bool, optional
        Whether the source is local or remote, by default True
    """
    if src_is_local:
        if Path(src).exists():
            if Path(src).is_dir():
                dst = "/".join(dst.split("/")[:-1])
                if not SSH_path_exists(ssh, dst):
                    SSH_makedirs(ssh, dst)
                scp.put(
                    files=[src],
                    remote_path=dst, recursive=True)
            else:
                parent_of_dst = "/".join(dst.split("/")[:-1])
                if not SSH_path_exists(ssh,parent_of_dst):
                    SSH_makedirs(ssh, parent_of_dst)
                scp.put(
                    files=[src],
                    remote_path=dst)
    else:
        if SSH_path_exists(ssh, src):
            if SSH_isdir(ssh, src):
                scp.get(src, dst, recursive=True)
            else:
                scp.get(src, dst)

import re
# # TODO:
def SCP_synctree(ssh: SSHClient, scp: SCPClient, src: str, dst: str, src_is_local: bool = True, exclude_regex: str = "", verbose = False) -> None:
    """
    This function synchronizes a directory between the local machine and the vpu

    Parameters
    ----------
    ssh : SSHClient
        ssh library native handle
    scp : SCPClient
        scp library native handle
    src : str
        path to source directory
    dst : str
        path to destination directory
    src_is_local : bool, optional
        Whether the source is local or remote, by default True
    """
    
    if src_is_local:
        src = expand_pc_path(src)
        dst = expand_remote_path(dst)

        logger.info(f"Syncing {src} to {dst} excluding {exclude_regex}")
        for root, dirs, files in os.walk(src):
            relative_root = Path(root).as_posix().replace(src, "").replace("\\", "/")
            if re.search(exclude_regex, relative_root+"/") is None:
                if verbose:
                    logger.info(f"|-- {relative_root}/")
                for file in files:
                    if re.search(exclude_regex, file) is None:
                        src_file = "/".join((src+ relative_root, file))
                        dst_file = "/".join((dst+ relative_root, file))
                        try:
                            SCP_transfer_item(ssh, scp, src_file, dst_file, src_is_local=True,)
                        except Exception as e:
                            logger.error(f"Error transferring {src_file} to {dst_file}")
    else:
        raise NotImplementedError("SCP_synctree not yet implemented for remote source")



if __name__ == "__main__":
    ...
    #%%
    ssh, scp = SSH_collect_OVP_handles()

    SCP_transfer_item(ssh, scp, "C:/Users/rober/Downloads/ovp8xx/docker/ovp_docker_utils/ssh_file_utils.py", "/home/oem/tmp/ssh_file_utils.py", src_is_local=True)