#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import os
import re
from pathlib import Path
import sys
import logging
import time
from datetime import datetime
import subprocess
import threading
from typing import Union, List

from pydantic import BaseModel
from paramiko.client import SSHClient
from scp import SCPClient
import semver

try:
    import ifm3dpy
    USING_IFM3DPY = True
except ImportError:
    USING_IFM3DPY = False

from .defaults import DEFAULT_IP
from .ssh_file_utils import SSH_collect_OVP_handles, SSH_listdir, SSH_path_exists, SSH_isdir, SSH_makedirs, SCP_transfer_item, expand_pc_path, expand_remote_path
from .docker_compose_instance import DockerComposeServiceInstance
from .ssh_key_gen import assign_key

USING_IPYTHON = "ipykernel" in sys.modules
if USING_IPYTHON:
    logger = logging.getLogger("notebook")
else:
    logger = logging.getLogger("deploy")


# Setup console logging 
log_format = "%(asctime)s:%(filename)-8s:%(levelname)-8s:%(message)s"
datefmt = "%y.%m.%d_%H.%M.%S"
console_log_level = logging.INFO
logging.basicConfig(format=log_format,stream=sys.stdout,
                    level=console_log_level, datefmt=datefmt)


TESTED_COMPATIBLE_FIRMWARE_RANGES = [
    ["1.1.0", "1.5.999"],
]

def ovp_present(IP: str = os.environ.get("IFM3D_IP", DEFAULT_IP), USING_IFM3DPY: bool = ("ipykernel" in sys.modules)) -> bool:
    if USING_IFM3DPY:
        logger.info(f"Using ifm3dpy=={ifm3dpy.__version__}")
    else:
        logger.info("ifm3dpy unavailable")

    logger.info(f"Checking for ovp at {IP}")
    if USING_IFM3DPY:
        o3r = ifm3dpy.O3R(IP)
        config = o3r.get()
        logger.info(f"OVP is connected at {IP}")
        ovp_found = True
    else:
        logger.info("Trying to connect to OVP without ifm3d")
        with subprocess.Popen(['ping', IP], stdout=subprocess.PIPE) as process:
            # Get rid of the first line output from the ping cmd
            output = process.stdout.readline().decode()
            ovp_found = False
            while True:
                output = process.stdout.readline().decode()
                if "unreachable".lower() in output.lower():
                    break
                if "bytes" and IP in output:
                    ovp_found = True
                    break
        ovp_found_str = {False: "not ", True: ""}[ovp_found]
        logger.info(
            f"Device is {ovp_found_str}connected at {IP}")

    return ovp_found

def structure_docker_table_output(docker_table: List[str]) -> List[dict]:
    """
    This function structures the output of a docker table into a list of dictionaries    
    """
    params = [param.strip() for param in docker_table[0].split("  ")if param]
    param_starting_positions = []
    param_end_positions = []
    cursor = 0
    for param in params:
        for i in range(cursor, len(docker_table[0])):
            if docker_table[0][i:].startswith(param):
                param_starting_positions.append(i)
                cursor = i + len(param)
                break
    param_end_positions = param_starting_positions[1:] + [
        max([len(line) for line in docker_table])]
    entry_dicts = []
    for running_container in docker_table[1:]:
        container_dict = {}
        for param, param_starting_position, param_end_position in zip(params, param_starting_positions, param_end_positions):
            container_dict[param] = running_container[param_starting_position:param_end_position].strip(
            )
        entry_dicts.append(container_dict)
    return entry_dicts


def attach_to_ssh_cmd(ip: str, cmd: str, stop_loop, private_key_path: str, password: str = "oem",  timeout: float = 0, output_buffer: str = "") -> str:
    """
    This function runs a command on the remote device and prints the output to the console

    Parameters
    ----------
    ip : str
        IP address of the device
    cmd : str
        command to run on the device
    stop_loop : bool
        thread safe callable flag to stop the loop
    private_key_path : str
        path to private key
    password : str
        password for the device
    timeout : int
        time to run the loop for
    output_buffer : str
        buffer to store output

    Returns
    -------
    str
        output of the command
    """
    ssh, scp = SSH_collect_OVP_handles(
        IP=ip, password=password, private_key_path=private_key_path)
    ssh: SSHClient = ssh
    transport = ssh.get_transport()
    channel = transport.open_session()
    channel.get_pty()
    channel.exec_command(cmd)

    start = time.perf_counter()
    output_buffer += [""]
    try:
        while not channel.exit_status_ready() and (timeout<1 or (time.perf_counter() < start+timeout)) and not stop_loop():
            if channel.recv_ready():
                output = channel.recv(1024).decode()
                if output:
                    print(output, end="")
                    output_buffer[-1] += output
            else:
                time.sleep(0.02)
    except KeyboardInterrupt:
        pass
    return output_buffer


class OVPHandleConfig(BaseModel):
    IP: str = os.environ.get("IFM3D_IP", DEFAULT_IP)
    possible_initial_ip_addresses_to_try: List[str] = []
    iface: str = "eth0"
    gateway: str = ""
    netmask: int = 24
    ssh_key_dir: str = "~/.ssh/"
    oem_user_password: str = "oem"
    ssh_key_file_name: str = "id_rsa"


class OVPHandle:
    def __init__(
        self,
        config: OVPHandleConfig = OVPHandleConfig(),
    ):
        """
        This class handles the deployment of docker containers to the OVP8XX. It is a thin wrapper around the ifm3dpy library, the paramiko and scp libraries for SSH and SCP respectively, and the docker command line interface on the OVP.

        The objective here is to minimize magic and maximize transparency. The user should be able to see exactly what is happening on the OVP and be able to interact with the OVP directly if desired. OVPHandle.o3r is the native ifm3dpy handle to the OVP. OVPHandle.ssh and OVPHandle.scp are the native paramiko and scp handles to the OVP respectively.

        Each cli command run on the OVP (outside of simple filesystem operations from ovp_docker_utils.ssh_file_utils) is logged so that issues can be debugged if they arise.
        """

        self.config: OVPHandleConfig = config

        self._connected = False
        self._o3r = None
        self._ssh = None
        self._scp = None
        self._fw_version = None
        self.private_key_path = None

        self.connect()

    @property
    def log_file_path(self):
        return self._log_file_path

    @property
    def connected(self):
        return self._connected

    @property
    def o3r(self):
        return self._o3r

    @property
    def ssh(self):
        return self._ssh

    @property
    def scp(self):
        return self._scp

    @property
    def vpu_config(self):
        if not self._o3r:
            raise Exception("Not connected to ovp")
        return self._o3r.get()

    @property
    def fw_version(self):
        if not self._o3r:
            raise Exception("Not connected to ovp")
        return self._fw_version

    @property
    def vpu_sn(self):
        return self.vpu_config["device"]["info"]["serialNumber"]

    @property
    def vpu_name(self):
        return self.vpu_config["device"]["info"]["name"]

    def connect(self, reboot_pause=160) -> bool:
        OVP_config = None
        self._connected = False

        possible_initial_ip_addresses = self.config.possible_initial_ip_addresses_to_try
        if self.config.IP not in possible_initial_ip_addresses:
            possible_initial_ip_addresses.insert(0, self.config.IP)
        logger.info(
            f"Trying to connect to OVP at any of the following addresses: {possible_initial_ip_addresses}")
        for ip_addr_to_check in possible_initial_ip_addresses:
            try:
                OVP_config = ifm3dpy.O3R(ip_addr_to_check).get()
                break
            except ifm3dpy.device.Error as e:
                pass

        if OVP_config is None:
            self._connected = False
            raise Exception(f"No ovp found at any of the specified IP addresses: {possible_initial_ip_addresses}.")
        else:
            self._connected = True
            logger.info(f"Connected to {ip_addr_to_check}")
            iface_settings = OVP_config["device"]["network"]["interfaces"][self.config.iface]["ipv4"]
            specified_address = self.config.IP
            specified_netmask = self.config.netmask
            if self.config.gateway:
                gateway_in_address_subnet = ".".join(self.config.gateway.split(".")[:specified_netmask//8]) == ".".join(specified_address.split(".")[:specified_netmask//8])
                assert gateway_in_address_subnet
                specified_gateway = self.config.gateway
            else:
                gateway_in_address_subnet = ".".join(specified_address.split(".")[:specified_netmask//8]) == ".".join(iface_settings["gateway"].split(".")[:specified_netmask//8])
                if gateway_in_address_subnet:
                    specified_gateway = iface_settings["gateway"]
                else:
                    raise Exception(f"Gateway not specified and currently ({iface_settings['gateway']}) not in the same subnet as the specified IP address ({specified_address}). please specify a gateway")        

            new_iface_settings = {
                "address": specified_address,
                "gateway": specified_gateway,
                "mask": specified_netmask
            }
            if specified_address != iface_settings["address"] or specified_gateway != iface_settings["gateway"] or specified_netmask != iface_settings["mask"]:
                logger.info(f"Updating {self.config.iface} from {iface_settings} to {new_iface_settings} and rebooting")

                ifm3dpy.O3R(ip_addr_to_check).set({"device": {"network": {"interfaces": {self.config.iface: {
                    "ipv4": new_iface_settings}}}}})
                
                ifm3dpy.O3R(ip_addr_to_check).reboot()
                logger.info(f"Waiting {reboot_pause}s for OVP to reboot.")
                heartbeat_rate = 2
                for x in range(int(reboot_pause/heartbeat_rate)):
                    print(".", end="")
                    time.sleep(heartbeat_rate)
                print()
                for attempt in range(3):
                    try:
                        new_config = ifm3dpy.O3R(specified_address).get()
                        break
                    except Exception as e:
                        logger.info(f"Attempt {attempt+1} to reconnect failed: {e}")
                        time.sleep(10)

        if self._connected:
            self._o3r = ifm3dpy.O3R(self.config.IP)
            self._fw_version = ".".join(self.vpu_config["device"]["swVersion"]["firmware"].split(
                # get the first 3 parts of the version number
                "-")[0].split(".")[:3])

            logger.info(f"OVP8xx firmware version: {self._fw_version}")

            # Check for firmware compatibility
            if not any(
                    [(semver.compare(self._fw_version, range[0]) >= 0 and semver.compare(range[1], self._fw_version) >= 0) for range in TESTED_COMPATIBLE_FIRMWARE_RANGES]):
                raise Exception(
                    f"OVP8xx firmware version {self._fw_version} is specified to be compatible with version of the deployment ovp (tested with the following ranges: {TESTED_COMPATIBLE_FIRMWARE_RANGES})")

            self.private_key_path = assign_key(
                ip=self.config.IP, target_dir=self.config.ssh_key_dir, key_title=self.config.ssh_key_file_name)

            logger.info(f"private_key_path = {self.private_key_path}")

            try:
                self._ssh, self._scp = SSH_collect_OVP_handles(
                    IP=self.config.IP, password=self.config.oem_user_password, private_key_path=self.private_key_path)
            except Exception as e:
                logger.info(
                    f"OVPHandle is present but failed to connect via ssh: {e}")
                self._connected = False
                raise e

            logger.info(
                f"OVPHandle accessible using ifm3dpy=={ifm3dpy.__version__} and ssh connected")
        return self._connected

    def mkdir(self, dir_path: str) -> None:
        if not SSH_path_exists(self._ssh, dir_path):
            cmd = f"mkdir {dir_path}"
            logger.info(cmd)
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            logger.info(
                f">>> {_stderr.read().decode().strip()} {_stdout.read().decode().strip()}")

    def append_deployment_timestamp(self, deployment_timestamp_path: str = "~/share/Deployments") -> None:
        cmd = f'echo "{Path(self._log_file_path).name[:-4]}" >> {deployment_timestamp_path}'
        logger.info(cmd)
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        logger.info(
            f">>> {_stderr.read().decode().strip()} {_stdout.read().decode().strip()}")

    def append_docker_registry(self, docker_registry_host: str = "", docker_registry_port: int = 5000, timeout=100) -> None:
        insecure_registries = self.vpu_config["device"]["docker"]["insecure-registries"]
        if docker_registry_host and docker_registry_port:
            if f"{docker_registry_host}:{docker_registry_port}" not in insecure_registries:
                logger.info(
                    f"Adding {docker_registry_host}:{docker_registry_port} to insecure registries in OVP config")
                if len(insecure_registries) > 2:
                    logger.warning(
                        f"OVP already has {len(insecure_registries)} insecure registries, adding more is not permitted, the last one will be replaced")
                    insecure_registries.pop()
                insecure_registries.append(
                    f"{docker_registry_host}:{docker_registry_port}")
                self._o3r.set(
                    {"device": {"docker": {"insecure-registries": insecure_registries}}})
                logger.info(
                    f"Success! {docker_registry_host}:{docker_registry_port} added to insecure registries in OVP config, restarting the vpu to apply changes")
                self._o3r.reboot()
                logger.info(
                    f"OVP rebooting, waiting {timeout}s for it to come back online")
                heartbeat_rate = 2
                for x in range(timeout//heartbeat_rate):
                    print(".", end="")
                    time.sleep(heartbeat_rate)
                self.connect()

            else:
                logger.info(
                    f"{docker_registry_host}:{docker_registry_port} already in insecure registries in OVP config")

    def transfer_to_vpu(self, src: str, dst: str, verbose = True) -> None:
        src = expand_pc_path(src)
        dst = expand_remote_path(dst)
        if Path(src).exists():
            if verbose:
                logger.info(
                    f"transferring {src} to {dst}")
            SCP_transfer_item(
                self._ssh, self._scp, src, dst, True)
        else:
            logger.info(f"file not found '{src}'")

    def transfer_from_vpu(self, src: str, dst: str) -> None:
        src = expand_remote_path(src)
        dst = expand_pc_path(dst)
        if SSH_path_exists(self._ssh, src):
            logger.info(
                f"Transferring {src} to {dst}")
            SCP_transfer_item(
                self._ssh, self._scp, src, dst, False)
        else:
            logger.info(f"file not found '{src}'")

    def get_running_docker_containers(self) -> List[str]:
        cmd = "docker ps -a"
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        running_containers_list = _stdout.read().decode().strip().split("\n")
        return structure_docker_table_output(running_containers_list)

    def remove_running_docker_containers(self, running_containers_to_remove: list = []) -> None:
        for running_container in running_containers_to_remove:
            cmd = f"docker rm -f {running_container['CONTAINER ID']}"
            logger.info(cmd)
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            logger.info(f">>>{_stdout.read().decode().strip()}")

    def get_cached_docker_images(self) -> List[str]:
        cmd = "docker image ls -a"
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        cached_images_list = _stdout.read().decode().strip().split("\n")
        return structure_docker_table_output(cached_images_list)

    def remove_cached_docker_images(self, cached_images_to_remove: list = []) -> None:
        for cached_container in cached_images_to_remove:
            cmd = f"docker image rm {cached_container['IMAGE ID']}"
            logger.info(cmd)
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            logger.info(f">>>{_stdout.read().decode().strip()}")

    def get_registered_docker_volumes(self) -> List[str]:
        cmd = "docker volume ls -a"
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        cached_images_list = _stdout.read().decode().strip().split("\n")
        return structure_docker_table_output(cached_images_list)

    def remove_registered_docker_volumes(self, registered_volumes_to_remove: list = []) -> None:
        for volume in registered_volumes_to_remove:
            cmd = f"docker volume rm {volume['VOLUME NAME']}"
            logger.info(cmd)
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            logger.info(f">>>{_stdout.read().decode().strip()}")

    def set_vpu_name(self, set_vpu_name: str) -> None:
        logger.info(f"Setting device name to {set_vpu_name}")
        self._o3r.set({"device": {"info": {"name": set_vpu_name}}})

    def mount_usb(self) -> list:
        cmd = f"mount"
        logger.info(cmd)
        _stdin, _stdout, _stderr = self.ssh.exec_command(cmd)
        output = _stdout.read().decode().strip()
        logger.info(">>>" + output.split("\n")
                    [0] + " ..." + _stderr.read().decode().strip())
        mounted_disks_dirs = [disk_desc.split(
            " ")[2] for disk_desc in output.split("\n") if ("autofs" in disk_desc)]
        return mounted_disks_dirs

    def disk_is_available(self, known_disk_name: str) -> bool:
        self.mount_usb()
        disk_dir = "/run/media/system/" + known_disk_name
        logger.info(f"Checking if disk is available at {disk_dir}")
        disk_is_available = SSH_path_exists(self._ssh, disk_dir)
        return disk_is_available

    def setup_docker_volume(self, path_for_volume_to_mount: str, volume_name: str) -> None:
        # setup volume as specified
        cmd = f'docker volume create --driver local\
              -o o=bind -o type=none -o device="{path_for_volume_to_mount}" {volume_name}'
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        logger.info(cmd)
        if _stdout.read().decode().strip() == volume_name:
            logger.info("Success!")
        else:
            logger.info("Issue encountered while setting up shared volume")
            raise Exception(_stderr.read().decode().strip())

    def import_docker_image(self, image_to_import: str) -> None:
        # import image
        docker_image_fname = Path(image_to_import).name
        logger.info("importing image into vpu docker storage")
        cmd = f"cat {image_to_import}|docker import - {docker_image_fname[:-4]}"
        logger.info(cmd)
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        logger.info(">>>"+_stdout.read().decode().strip() +
                    _stderr.read().decode().strip())

    def load_docker_image(self, image_to_load: str, update_tag_on_OVP_to: str = "") -> None:
        # load image
        docker_image_fname = Path(image_to_load).name
        logger.info("loading image into vpu docker storage")
        cmd = f"docker load -i {image_to_load}"
        logger.info(cmd)
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        stdout = _stdout.read().decode().strip()
        logger.info(">>>"+stdout +
                    _stderr.read().decode().strip())
        if "Loaded image" not in stdout:
            logger.warning("Issue encountered while loading image")
        elif update_tag_on_OVP_to:
            tag_of_loaded_image = stdout.strip().split(" ")[-1]
            cmd = f"docker tag {tag_of_loaded_image} {update_tag_on_OVP_to}"
            logger.info(cmd)
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            logger.info(">>>"+_stdout.read().decode().strip() +
                        _stderr.read().decode().strip())

    def pull_docker_image_from_registry(self, docker_registry_host: str, docker_registry_port: int, docker_tag: str, update_tag_on_OVP_to: str = "") -> None:
        if ":" not in docker_tag:
            docker_tag += ":latest"

        # pull image
        logger.info("pulling image from local registry (this may take a while)")
        cmd = f"docker pull {docker_registry_host}:{docker_registry_port}/{docker_tag}"
        logger.info(cmd)
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        logger.info(">>>"+_stdout.read().decode().strip() +
                    _stderr.read().decode().strip())

        if update_tag_on_OVP_to:
            cmd = f"docker tag {docker_registry_host}:{docker_registry_port}/{docker_tag} {update_tag_on_OVP_to}"
            logger.info(cmd)
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            logger.info(">>>"+_stdout.read().decode().strip() +
                        _stderr.read().decode().strip())

    def rm_item(self, item_to_rm: str) -> None:
        if SSH_path_exists(self._ssh, item_to_rm):
            logger.info(f"Removing {item_to_rm}")
            if SSH_isdir(self._ssh, item_to_rm):
                cmd = f"rm -r {item_to_rm}"
                logger.info(cmd)
                _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
                logger.info(_stdout.read().decode().strip() +
                            _stderr.read().decode().strip())
            else:
                cmd = f"rm {item_to_rm}"
                logger.info(cmd)
                _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
                logger.info(">>>"+_stdout.read().decode().strip() +
                            _stderr.read().decode().strip())

    def enable_autostart(self, docker_compose_fname: str, service_name: str) -> None:
        # check if symlink already exists
        docker_compose_dir = f"/usr/share/oem/docker/compose/{service_name}"

        docker_compose_vpu_path = docker_compose_dir+"/docker-compose.yml"

        if not SSH_path_exists(self._ssh, docker_compose_vpu_path):
            logger.info(
                "no docker-compose symlink for auto-start found, setting it up now")
            SSH_makedirs(self._ssh, docker_compose_dir)
            cmd = f"ln -s {docker_compose_fname} {docker_compose_vpu_path}"
            logger.info(cmd)
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            logger.info(
                f">>> {_stderr.read().decode().strip()} {_stdout.read().decode().strip()}")

        logger.info("Enabling autostart...")
        cmd = f'systemctl --user enable oem-dc@{service_name}'
        logger.info(cmd)
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        output = _stdout.read().decode().strip()

    def autostart_enabled(self, service_name: str) -> bool:
        cmd = f"systemctl --user status oem-dc@{service_name}"
        logger.info(cmd)
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        # logger.info(
        #     f">>> {_stderr.read().decode().strip()} {_stdout.read().decode().strip()}")
        output = _stdout.read().decode().strip()
        return "enabled;" in output

    def get_all_autostart_instances(self) -> List[str]:
        cmd = f"ls /home/oem/.config/systemd/user/default.target.wants/"
        logger.info(cmd)
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        output = _stdout.read().decode().strip()
        # Regular expression pattern
        pattern = r'oem-dc@(.*?).service'
        # Find matches
        matches = re.findall(pattern, output)
        logger.info(">>>" + output)
        return matches

    def disable_autostart(self, service_name: str) -> None:
        logger.info("disabling autostart...")
        cmd = f'systemctl --user disable oem-dc@{service_name}'
        logger.info(cmd)
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        logger.info(
            f">>> {_stderr.read().decode().strip()} {_stdout.read().decode().strip()}")

    def stop_container(self, service_name: str):
        cmd = f"docker rm -f {service_name}"
        logger.info(f"Stopping container with: {cmd}")
        _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
        logger.info(">>>" + _stdout.read().decode().strip() +
                    _stderr.read().decode().strip())

    def pull_journalctl_logs(self, dst_dir: Union[Path, str], dst_name="") -> List[str]:
        if not dst_name:
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            dst_name = f"journalctl_{ts}.gzip"
        fname = "journalctl.gzip"
        logger.info(f"journalctl | gzip > {fname}")
        _stdin, _stdout, _stderr = self._ssh.exec_command(
            f"journalctl | gzip > {fname}")
        logger.info(
            f">>> {_stderr.read().decode().strip()} {_stdout.read().decode().strip()}")
        if type(dst_dir) == str:
            dst_dir = Path(dst_dir).expanduser().absolute()
        logger.info(dst_dir/dst_name)
        self.transfer_from_vpu("/home/oem/"+fname, dst_dir/dst_name)

    def initialize_container(self, service: DockerComposeServiceInstance, pipe_duration: float = 0, stop_upon_exit: bool = False, autostart_enabled=True, trigger_to_close_container: str = "") -> None:
        initialized = False

        non_standard_docker_logger_used = service.log_driver is not None

        docker_compose_dir = f"/usr/share/oem/docker/compose/{service.service_name}"

        detach_arg = "-d" if pipe_duration == 0 or non_standard_docker_logger_used else ""
        attachment_addendum = f"&& docker attach {service.container_name}" if non_standard_docker_logger_used and pipe_duration != 0 else ""
        if autostart_enabled:
            cmd = f"cd {docker_compose_dir} && docker-compose up {detach_arg} --remove-orphans {service.service_name} {attachment_addendum}"
        else:
            cmd = f"docker-compose -f {service.docker_compose_dst_on_vpu} up {detach_arg} --remove-orphans {service.service_name} {attachment_addendum}"

        logger.info(cmd)
        if pipe_duration == 0:
            _stdin, _stdout, _stderr = self._ssh.exec_command(cmd)
            output_lines_from_container = _stdout.read().decode().strip().split("\n")
            logger.info(
                f">>> {_stderr.read().decode().strip()} {' '.join(output_lines_from_container)}")
            logger.info(
                f"{service.service_name} initialized from {service.docker_compose_dst_on_vpu}")
        else:
            output_lines_from_container = self.attach_to_container(
                cmd=cmd,
                container_name=service.container_name,
                pipe_duration=pipe_duration,
                stop_upon_exit=stop_upon_exit,
                trigger_to_close_container=trigger_to_close_container,
            )

        return output_lines_from_container

    def attach_to_container(self, cmd: str = "", container_name: str = "", pipe_duration: float = 20, stop_upon_exit: bool = False, trigger_to_close_container: str = "") -> List[str]:

        if not cmd:
            cmd = f"docker attach {container_name}"
        output_lines_from_container = [""]

        stop_loop = False
        print_loop_thread = threading.Thread(
            target=attach_to_ssh_cmd,
            args=(self.config.IP, cmd, lambda: stop_loop, self.private_key_path,
                  self.config.oem_user_password, pipe_duration, output_lines_from_container),
            daemon=True
        )
        len_output_buffer = 0
        print_loop_thread.start()
        start_t = time.perf_counter()
        while not stop_loop:
            try:
                time.sleep(0.2)
                if pipe_duration > 0 and time.perf_counter() > start_t+pipe_duration:
                    logger.info(
                        f"run_duration of {pipe_duration} seconds has been reached, detaching from container...")
                    stop_loop = True
                else:
                    # check if new output lines have been added
                    if len(output_lines_from_container[-1]) > len_output_buffer:
                        latest_lines = output_lines_from_container[-1][len_output_buffer:]
                        len_output_buffer = len(output_lines_from_container[-1])
                        if any([" exited with code 0\n\x1b[0m" in latest_lines]):
                            logger.info("Container exited with code 0")
                            stop_loop = True
                        if trigger_to_close_container and any([trigger_to_close_container in latest_lines]):
                            logger.info(
                                f"Container exited with trigger: {trigger_to_close_container}")
                            stop_loop = True
            except KeyboardInterrupt:
                logger.info(
                    "KeyboardInterrupt detected, Detaching from container...")
                stop_loop = True

        if stop_upon_exit:
            logger.info("Stopping container...")
            self.stop_container(service_name=container_name)
            time.sleep(0.5)
        time.sleep(0.5)
        if not print_loop_thread.is_alive():
            print_loop_thread.join()
        else:
            logger.info(
                "Failed to stop container monitor thread... it will exit with the program exit")

        output_lines_from_container = output_lines_from_container.copy()
        del (print_loop_thread)
        time.sleep(2)

        logger.info("Container monitor thread stopped")

        return output_lines_from_container
