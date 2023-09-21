#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%#########################################
# Some boilerplate for automating deployment
# of dockerized applications.
#############################################

import os
from pathlib import Path
import argparse
import sys
import logging
import time
from datetime import datetime
import subprocess
import shlex
import select

from paramiko import AutoAddPolicy
from paramiko.client import SSHClient
from scp import SCPClient
import yaml


def SSH_listdir(ssh: SSHClient, path: str = "~") -> bool:
    cmd = f"ls {path}"
    _stdin, _stdout, _stderr = ssh.exec_command(cmd)
    return _stdout.read().decode().strip().split("\n")


def SSH_path_exists(ssh: SSHClient, path: str = "~") -> bool:
    cmd = f"cd {path}"
    _stdin, _stdout, _stderr = ssh.exec_command(cmd)
    if _stderr.read():
        tokenized_path = path.split("/")
        if len(tokenized_path) > 1:
            path_exists = tokenized_path[-1] in SSH_listdir(
                ssh, "/".join(tokenized_path[:-1]))
        else:
            path_exists = False
    else:
        path_exists = True
    return path_exists


def SSH_isdir(ssh: SSHClient, path: str = "~") -> bool:
    cmd = f"cd {path}"
    _stdin, _stdout, _stderr = ssh.exec_command(cmd)
    return not bool(_stderr.read().decode())


def SSH_makedirs(ssh: SSHClient, path: str = ""):
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


def transfer_item(scp: SCPClient, ssh: SSHClient, src: str, dst: str, src_is_local: bool = True):
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
                scp.put(
                    files=[src],
                    remote_path=dst)
    else:
        if SSH_path_exists(ssh, src):
            if SSH_isdir(ssh, src):
                scp.get(src, dst, recursive=True)
            else:
                scp.get(src, dst)


# %%#####################################
# Check Arguments, most default arguments are used if running interactively
#########################################
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="ifm ods example",
    )

    DEFAULT_IP = "192.168.0.69"
    IP = os.environ.get("IFM3D_IP", DEFAULT_IP)
    parser.add_argument(
        "--IP", type=str, default=DEFAULT_IP, help=f"IP address to be used, defaults to environment variable 'IFM3D_IP' if present, otherwise camera default: '{DEFAULT_IP}'"
    )

    log_level = ""
    log_level = "INFO"
    parser.add_argument(
        "--log_level", type=str, default=log_level, help=f"log file level (DEBUG,..,EXCEPTION), Defaults to {log_level} (no log file)"
    )

    transfers = ""
    transfers = "./oem_logging.py>~/oem_logging.py,./configs>~/configs"
    parser.add_argument("-t", "--transfers", type=str, default=transfers,
                        help=f"List of files/directories to transfer between the vpu and pc as pc/path>vpu/path or pc/path>vpu/path, Defaults to {transfers}",)

    docker_build = "./python_deps.Dockerfile>./docker_python_deps.tar"
    docker_build = ""
    parser.add_argument("--docker_build", type=str, default=docker_build,
                        help=f"path to dockerfile and output image file, if empty, no build will be triggered. Defaults to {''}",
                        )

    setup_docker_compose = ""
    setup_docker_compose = "./example_dc.yml,./docker_python_deps.tar,/home/oem,oemhomedir"
    parser.add_argument(
        "--setup_docker_compose", type=str, default=setup_docker_compose, help=f'Comma separated list of arguments needed to deploy docker-compose project, e.g.: "path/to/docker-compose/yaml/file,path/to/docker_image.tar,path/which/volume/should/mount,name_of_volume" , Defaults to {""}',
    )

    enable_autostart = ""
    parser.add_argument(
        "--enable_autostart", type=str, default=enable_autostart, help=f"List of container names as specified in their docker-compose file separated by commas. Note that --setup_docker_compose option must be used or have been used for each container previously, Defaults to {''}",
    )

    disable_autostart = ""
    parser.add_argument(
        "--disable_autostart", type=str, default=disable_autostart, help=f"List of container names separated by commas, Defaults to {''}",
    )

    log_caching = "/home/oem/logs>./logs/From_VPUs"
    parser.add_argument(
        "--log_caching", type=str, default=log_caching, help=f"specifies how to cache logs from VPU and won't cache anything if blank, Defaults to {log_caching}"
    )

    initialize = "example_dc.yml"
    parser.add_argument(
        "--initialize", type=str, default="", help=f"Name of the docker-compose yaml file to initialize. If empty, will not (re)initialize container, Defaults to {''}"
    )

    attach_to = "example_container"
    parser.add_argument(
        "--attach_to", type=str, default="", help=f"Name of the container to attach to. If empty, will not attach to container, Defaults to {''}"
    )

    set_vpu_name = "oem_app_test_vpu_000"
    parser.add_argument(
        "--set_vpu_name", type=str, default=set_vpu_name, help=f"What to update the name of the vpu to. If empty, will not assign a name to the attached vpu, Defaults to {set_vpu_name}"
    )

    USING_IPYTHON = "ipykernel" in sys.modules
    if not USING_IPYTHON:
        args = parser.parse_args()

        IP = args.IP
        docker_build = args.docker_build
        transfers = args.transfers
        setup_docker_compose = args.setup_docker_compose
        enable_autostart = args.enable_autostart
        disable_autostart = args.disable_autostart
        log_caching = args.log_caching
        initialize = args.initialize
        attach_to = args.attach_to
        set_vpu_name = args.set_vpu_name

    # %%######################################
    # Configure logging
    #########################################
    ts_format = "%y.%m.%d_%H.%M.%S%z"
    now = datetime.now().astimezone()
    now_local_ts = now.strftime(ts_format)

    console_level = logging.DEBUG
    file_level = logging.DEBUG

    # Setup console logging
    log_format = "%(asctime)s:%(filename)-8s:%(levelname)-8s:%(message)s"
    datefmt = "%y.%m.%d_%H.%M.%S"
    logging.basicConfig(format=log_format,
                        level=console_level, datefmt=datefmt)
    if USING_IPYTHON:
        logger = logging.getLogger("notebook")
    else:
        logger = logging.getLogger("root")

    # Add log file handler
    if log_level:
        log_dir = Path(__file__).parent/"logs"
        deployment_logs_subdir = log_dir/"Deployments"
        try:
            os.makedirs(deployment_logs_subdir)
        except OSError:
            ...
        log_fname = f"{now_local_ts}_{set_vpu_name}.log"
        fhandler = logging.FileHandler(
            filename=deployment_logs_subdir/log_fname, mode='a')
        formatter = logging.Formatter(log_format, datefmt)
        fhandler.setFormatter(formatter)
        fhandler.setLevel(logging.getLevelName(log_level))
        logger.addHandler(fhandler)

    # %%#####################################
    # Check if vpu is present
    #########################################

    try:
        import ifm3dpy
        USING_IFM3DPY = True
        logger.info(f"Using ifm3dpy=={ifm3dpy.__version__}")
    except:
        USING_IFM3DPY = False
        logger.info("ifm3dpy unavailable")

    if USING_IFM3DPY:
        o3r = ifm3dpy.O3R()
        config = o3r.get()
        logger.info(f"VPU is connected at {IP}")
        device_found = True
    else:
        with subprocess.Popen(['ping', IP], stdout=subprocess.PIPE) as process:
            # process = subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE)
            device_found = False
            buffer = ""
            while True:
                output = process.stdout.readline().decode()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    buffer += output
                    # print(output, end ="")
                if f"Reply from {IP}" in buffer:
                    device_found = True
                    break
        logger.info(
            f"Device is { {False: 'not ',True:''}[device_found]}connected at {IP}")
    if not device_found:
        sys.exit(0)

    # %%######################################
    # configure ssh and scp handles
    ##########################################

    oem_username = "oem"
    password = "oem"
    port = 22

    logging.getLogger("paramiko").setLevel(logging.INFO)
    logging.getLogger("scp").setLevel(logging.INFO)

    ssh: SSHClient = SSHClient()
    ssh.set_missing_host_key_policy(AutoAddPolicy())
    try:
        ssh.connect(IP, username=oem_username,
                    password=password, timeout=1, port=22)
    except Exception as e:
        if "timed out" in str(e):
            logger.info(
                f"Attempt to connect to {oem_username}@{IP}:{port} timed out.")
        raise e

    scp = SCPClient(ssh.get_transport())

    # remove knownhosts
    known_hosts_path = Path("~/.ssh/known_hosts").expanduser()
    with open(known_hosts_path, "r") as f:
        lines = f.readlines()
    with open(known_hosts_path, "w") as f:
        f.write(
            "\n".join([line for line in lines if not (line.split(" ")[0] == IP)]))

    # %%#####################################
    # Perform any file transfers called for explicitly by arguments
    #########################################

    def transfer_files_from_args(scp: SCPClient, ssh: SSHClient, transfers: str = ""):
        """
        Transfers files based on a simple CLI-friendly syntax

        Parameters
        ----------
        scp : SCPClient
            scp library native handle
        ssh : SSHClient
            ssh library native handle
        transfers : list[str], optional
            List of files/directories to transfer between the vpu and pc as eg.:
            'pc/path/thing_to_transfer_to_vpu>vpu/path,pc/path<vpu/path/thing_to_transfer_from_vpu', by default ""
        """
        if transfers:
            transfers = transfers.split(",")
            route_tuples = {"to_vpu": [], "from_vpu": []}
            delimiter_options = {">": "to_vpu", "<": "from_vpu"}
            for transfer in transfers:
                delimiter = ""
                for delimiter_option in delimiter_options.keys():
                    if delimiter_option in transfer:
                        delimiter += delimiter_option
                pc_path, vpu_path = transfer.split(delimiter)
                pc_path = pc_path.replace("~", str(Path().home()))
                pc_path = pc_path.replace(
                    "./", str(Path(__file__).parent)+"/").replace("\\", "/")
                vpu_path = (vpu_path.replace("~", "/home/oem"))
                src_dst_tuple = {"<": (vpu_path, pc_path), ">": (
                    pc_path, vpu_path)}[delimiter]
                route_tuples[delimiter_options[delimiter]].append(
                    src_dst_tuple)
            for transfer_to_vpu in route_tuples["to_vpu"]:
                if Path(transfer_to_vpu[0]).exists():
                    logger.info(
                        f"transferring {transfer_to_vpu[0]} to {transfer_to_vpu[1]}")
                    transfer_item(
                        scp, ssh, transfer_to_vpu[0], transfer_to_vpu[1], True)
                else:
                    logger.info(f"file not found {transfer_to_vpu[0]}")
            for transfer_from_vpu in route_tuples["from_vpu"]:
                if SSH_path_exists(ssh, transfer_from_vpu[0]):
                    logger.info(
                        f"Transferring {transfer_from_vpu[0]} to {transfer_from_vpu[1]}")
                    transfer_item(
                        scp, ssh, transfer_from_vpu[0], transfer_from_vpu[1], False)
                else:
                    logger.info(f"file not found {transfer_from_vpu[0]}")

    transfer_files_from_args(scp, ssh, transfers)

    # %%#####################################
    # set device name if desired
    #########################################

    if USING_IFM3DPY and set_vpu_name:
        o3r = ifm3dpy.O3R(IP)
        o3r.set({"device": {"info": {"name": set_vpu_name}}})

    # %%#####################################
    # Sync logs from vpu if requested
    #########################################

    if USING_IFM3DPY and log_caching:
        o3r = ifm3dpy.O3R(IP)
        vpu_config = o3r.get()
        sn = vpu_config['device']["info"]["serialNumber"]
        name = vpu_config["device"]["info"]["name"]
        vpu_specific_log_cache_dir_name = f"sn{sn}"
        if name:
            vpu_specific_log_cache_dir_name += "_"+name

        vpu_log_dir, local_log_cache = log_caching.split(">")
        local_log_cache = Path(local_log_cache).expanduser().absolute()
        vpu_specific_local_cache_path = local_log_cache/vpu_specific_log_cache_dir_name

        logger.info(
            f"Merging {vpu_log_dir} into {vpu_specific_local_cache_path}")
        # There is some arbitrary behavior around how directories get merged when using scp get but the following works around it
        if not vpu_specific_local_cache_path.parent.exists():
            os.makedirs(vpu_specific_local_cache_path.parent)
        elif vpu_specific_local_cache_path.exists():
            for item in SSH_listdir(ssh, vpu_log_dir):
                scp.get(vpu_log_dir+"/"+item,
                        vpu_specific_local_cache_path, recursive=True)
        else:
            scp.get(vpu_log_dir, vpu_specific_local_cache_path, recursive=True)

    # %%#####################################
    # docker build
    #########################################

    if docker_build:
        logger.info(f"Attempting docker build")

        dockerfile_path, docker_build_output_path = docker_build.split(">")
        timeout_building_docker = 1000

        if Path(dockerfile_path).absolute().exists():
            dockerfile_path
        elif not Path(dockerfile_path).exists():
            raise Exception(f"No dockerfile path found at: {dockerfile_path}")

        cmd = f'docker build -f "{dockerfile_path}" . -o "type=tar,dest={docker_build_output_path}"'
        if os.name == "nt":
            logger.info(f"Attempting docker build via WSL...")
            cmd = "wsl " + cmd

        if USING_IPYTHON:
            logger.info(
                """...\n...Cannot show output while building container via ipython...\n...If desired, try running the command in a separate terminal: """)
        logger.info(cmd)

        start = time.perf_counter()
        with subprocess.Popen(
            shlex.split(cmd),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            universal_newlines=True,
        ) as process:
            buffer = ""
            while time.perf_counter() < start+timeout_building_docker:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    buffer += output
                    print(output.strip().decode())

    # %%#####################################
    # kill/remove/delete all other containers
    #########################################

    cmd = "docker ps -a"
    _stdin, _stdout, _stderr = ssh.exec_command(cmd)
    running_containers_list = _stdout.read().decode().strip().split("\n")
    header = running_containers_list[0]
    id_index = 0
    image_index = header.index("IMAGE")
    running_containers = running_containers_list[1:]
    logger.info(f"Running containers = {running_containers}")
    for running_container in running_containers:
        id = running_container[id_index:image_index].strip()
        cmd = f"docker rm -f {id}"
        logger.info(cmd)
        _stdin, _stdout, _stderr = ssh.exec_command(cmd)
        logger.info(f">>>{_stdout.read().decode().strip()}")

    cmd = "docker image ls"
    _stdin, _stdout, _stderr = ssh.exec_command(cmd)
    cached_images_list = _stdout.read().decode().strip().split("\n")
    header = cached_images_list[0]
    cached_images = cached_images_list[1:]
    id_index = header.index("IMAGE ID")
    created_index = header.index("CREATED")
    logger.info(f"Cached images = {cached_images}")
    for cached_container in cached_images:
        id = cached_container[id_index:created_index].strip()
        cmd = f"docker image rm {id}"
        logger.info(cmd)
        _stdin, _stdout, _stderr = ssh.exec_command(cmd)

    # %%#####################################
    # deploy the docker-compose based container configuration + container
    #########################################

    if setup_docker_compose:  # TODO move everything below into conditional
        ...
        # default -> ["./example_container_dc.yml", "./docker_python_deps.tar"]

        setup_docker_compose_list = setup_docker_compose.split(",")

        docker_image_path = setup_docker_compose_list[1]
        docker_image_fname = Path(docker_image_path).name
        transfer_item(scp, ssh, docker_image_path,
                      f"~/{docker_image_fname}", True)

        docker_compose_path = setup_docker_compose_list[0]
        docker_compose_fname = docker_compose_path.split("/")[-1]
        transfer_item(scp, ssh, docker_compose_path,
                      f"~/{docker_compose_fname}", True)

        with open(docker_compose_path, "r") as f:
            docker_compose = yaml.load(f, yaml.BaseLoader)

        service_name, service = [(service_name, service) for service_name, service in docker_compose["services"].items(
        ) if docker_image_fname[:-4] in service["image"].split(":latest")[0]][0]

        container_name = service["container_name"]
        logger.info(f"Deploying container '{container_name}'")

        # load image
        logger.info("loading image into vpu docker storage")
        cmd = f"cat {docker_image_fname}| docker import - {docker_image_fname[:-4]}"
        _stdin, _stdout, _stderr = ssh.exec_command(cmd)
        logger.info(_stdout.read().decode().strip() +
                    _stderr.read().decode().strip())

        # delete image
        logger.info("Removing .tar image file now that it is loaded")
        cmd = f"rm ~/{docker_image_fname}"
        _stdin, _stdout, _stderr = ssh.exec_command(cmd)

        # setup volume as specified
        path_for_volume_to_mount = setup_docker_compose_list[2]
        volume_name = setup_docker_compose_list[3]
        cmd = f'docker volume create --driver local -o o=bind -o type=none -o device="{path_for_volume_to_mount}" {volume_name}'
        _stdin, _stdout, _stderr = ssh.exec_command(cmd)
        if _stdout.read().decode().strip() == volume_name:
            logger.info("Success!")
        else:
            logger.info("Issue encountered while setting up shared volume")
            raise Exception(_stderr.read().decode().strip)

    # %%################################
    # TODO setup key-pair communication alleviating the need to type "oem" each time you connect
    ####################################

    # %%#####################################
    # TODO configure sntp and ethernet if desired
    #########################################

    # default to: "74.6.168.72"

    # %%#####################################
    # enable or disable autostart as specified
    #########################################
    enable_autostart = "example_container"

    if enable_autostart:
        for container_name in enable_autostart.split(","):
            # check if symlink already exists
            docker_compose_dir = f"/usr/share/oem/docker/compose/deploy/"

            docker_compose_path = docker_compose_dir+"/docker-compose.yml"

            if not SSH_path_exists(ssh, docker_compose_path):
                logger.info(
                    "no docker-compose symlink for auto-start found, setting it up now")
                SSH_makedirs(ssh, docker_compose_dir)
                docker_compose_home = "~/"+docker_compose_fname
                cmd = f"ln -s {docker_compose_home} {docker_compose_path}"
                _stdin, _stdout, _stderr = ssh.exec_command(cmd)

            cmd = f'systemctl --user enable oem-dc@{container_name}'
            _stdin, _stdout, _stderr = ssh.exec_command(cmd)

    if disable_autostart:
        for container_name in disable_autostart.split(","):
            cmd = f'systemctl --user disable oem-dc@{container_name}'
            _stdin, _stdout, _stderr = ssh.exec_command(cmd)

    # %%#####################################
    # initialize container
    #########################################

    initialize = "example_dc.yml"
    if initialize:
        ...
        cmd = f"docker-compose -f {initialize} up --detach"
        _stdin, _stdout, _stderr = ssh.exec_command(cmd)
        logger.info(cmd)
        logger.info(
            f">>> {_stderr.read().decode().strip()} {_stdout.read().decode().strip()}")

    # %%
    logger.info(f"Container initialized, now running...")
    transport = ssh.get_transport()
    channel = transport.open_session()
    channel.exec_command("docker attach example_container")
    try:
        while True:
            rl, wl, xl = select.select([channel], [], [], 0.0)
            if len(rl) > 0:
                # Must be stdout
                output = channel.recv(1024).decode()
                if output:
                    print(output, end="")
    except KeyboardInterrupt:
        channel.close()
        ssh.close()
        print("Detaching from container without killing it...")

    # %%
