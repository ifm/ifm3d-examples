# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import time
import os
import sys
from pathlib import Path
import socket
from typing import List
import inspect
import logging

import yaml

from . import logger, OVPHandle, OVPHandleConfig, DockerComposeServiceInstance

from .deployment_components import DeploymentComponents,demo_deployment_components

sys.path.append((Path(__file__).parent.parent/"python" /
                "ovp8xxexamples"/"core").absolute().as_posix())
try:
    from fw_update_utils import update_fw
except:
    logger.error("fw_update_utils not found")
    update_fw = None

notice = """Note:
This script is intended to be run on a PC to deploy a
docker image to an ovp8xx. It is recommended to understand
each section of the script before running it. The script is
intended to be used as a template and may need to be modified
to suit the specific needs of an application deployment.
"""

DEFAULT_SECONDS_OF_OUTPUT_TO_CAPTURE = 30
PARENT_DIR = Path(__file__).parent
EXAMPLES_DIR = PARENT_DIR.parent.parent
DEFAULT_TMP_DIR = str(PARENT_DIR / "tmp")
DEFAULT_IP = os.environ.get("IFM3D_IP", "192.168.0.69")

# %%#########################################
# Define the deployment function
#############################################

def deploy(
    service_name: str,

    reset_vpu: bool = False,

    docker_rebuild: bool = True,
    purge_docker_images_on_OVP: bool = False,
    replace_existing_image: bool = True,

    disable_autostart: bool = True,
    enable_autostart: bool = True,

    tar_image_transfer: bool = True,
    remove_tar_file_after_loading: bool = True,

    docker_registry_port: int = 5005,
    docker_registry_host_relative_to_pc: str = "localhost",

    tmp_dir: str = DEFAULT_TMP_DIR,

    ip: str = DEFAULT_IP,
    possible_initial_ip_addresses_to_try: List[str] = [],
    gateway: str = "",
    netmask: int = 24,
    time_server: str = "",
    can_bitrate: int = 0,

    ssh_key_file_name: str = "id_rsa_ovp8xx",

    firmware_image_to_use: str = "",
    firmware_version_to_use: str = "",

    seconds_of_output: int = DEFAULT_SECONDS_OF_OUTPUT_TO_CAPTURE,

    additional_deployment_components: bool = False,
):
    f"""
    {notice}

    You can simply build a container and transfer the .tar image file.

    Alternatively use a local registry. This requires starting the registry container prior to building a container and running deployment
    `docker run -d -p <docker_registry_port>:5000 --name registry registry:latest`
    Note that on some systems you may need to open the port in the firewall for incoming tcp connections to use registry ports.


    Args:
    service_name (str): Name of the service to deploy from.

    reset_vpu (bool, optional): Reset the OVP before deployment. Defaults to True.

    docker_rebuild (bool, optional): Rebuild the docker image. Defaults to True.
    purge_docker_images_on_OVP (bool, optional): Purge docker images on the OVP. Defaults to False.
    replace_existing_image (bool, optional): Replace existing image. Defaults to True.

    disable_autostart (bool, optional): Disable autostart of any existing docker-compose services. Defaults to True.
    enable_autostart (bool, optional): Enable autostart of the docker-compose service being deployed. Defaults to True.

    tar_image_transfer (bool, optional): Use tar file image transfer. Defaults to True.
    remove_tar_file_after_loading (bool, optional): Remove tar file after loading. Defaults to True.

    docker_registry_port (int, optional): Docker registry port. Defaults to 5005.
    docker_registry_host_relative_to_pc (str, optional): Docker registry host relative to PC. Defaults to "localhost".

    build_dir (str, optional): Build directory. Defaults to PARENT_DIR.
    tmp_dir (str, optional): Temporary directory. Defaults to PARENT_DIR / "tmp".

    IP (str, optional): IP address of the OVP. Defaults to {DEFAULT_IP}.
    possible_initial_ip_addresses_to_try (List[str], optional): Possible initial IP addresses to try. Defaults to [].
    gateway (str, optional): Gateway address. Defaults to "".
    netmask (int, optional): Netmask. Defaults to 24.
    time_server (str, optional): Time server address. Defaults to "".
    can_bitrate (int, optional): CAN bus Bitrate. Defaults to 0 (inactive).
    
    firmware_image_to_use (str, optional): Path to firmware image. Defaults to "".
    firmware_version_to_use (str, optional): Version to match. Defaults to "".

    seconds_of_output (int, optional): Seconds of output to capture from container. Defaults to {DEFAULT_SECONDS_OF_OUTPUT_TO_CAPTURE}.

    additional_deployment_components (bool, optional): Inaccessible via CLI, but can be used to extend the demo_deployment_components. Defaults to False.


    """

    
    # Setup console logging 
    log_format = "%(asctime)s:%(filename)-8s:%(levelname)-8s:%(message)s"
    datefmt = "%y.%m.%d_%H.%M.%S"
    console_log_level = logging.INFO
    logging.basicConfig(format=log_format,
                        level=console_log_level, datefmt=datefmt)

    logger.info(notice)
    # %%#########################################
    # Set options for the deployment process if running interactively
    #############################################

    # Leverage the default values of the deployment parameters if running interactively (useful for debug)
    if "ipykernel" in sys.modules:
        jupyter_notebook_args = {
            "service_name": list(demo_deployment_components.keys())[0], # pick the first service in the list or hardcode a service name
        }
        jupyter_notebook_args.update({k: v.default
                                      for k, v in inspect.signature(deploy).parameters.items() if (v.default != inspect.Parameter.empty) and (k not in locals())})
        locals().update(jupyter_notebook_args)

    # %%#########################################
    # Prepare to build the docker images if needed
    #############################################

    os.chdir(PARENT_DIR)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)


    # %%#########################################
    # Initialize the ovp object
    #############################################
    ovp = OVPHandle(
        OVPHandleConfig(
            IP=ip,
            possible_initial_ip_addresses_to_try=possible_initial_ip_addresses_to_try,
            gateway=gateway,
            netmask=netmask,
            ssh_key_file_name=ssh_key_file_name,
        )
    )

    # %%#########################################
    # Switch to the appropriate service to prepare the deployment
    #############################################

    if type(additional_deployment_components) == dict:
        demo_deployment_components.update(additional_deployment_components)

    service_components: DeploymentComponents = demo_deployment_components[service_name](
        **locals())
    service_instance_params: DockerComposeServiceInstance = service_components.docker_compose_service_instance()

    if docker_rebuild:
        service_components.docker_build_step()

    # %%#########################################
    # configure persistent network settings
    #############################################


    # persist the can0 baudrate setting  
    if can_bitrate:
        can_state = ovp.o3r.get()["ovp"]["network"]["interfaces"]["can0"]
        if can_state["active"] == False or can_state["bitrate"] != can_bitrate:
            logger.info("Setting up can0 interface...")
            ovp.o3r.set({"ovp": {"network": {"interfaces": {
                    "can0": {"active": True, "bitrate": can_bitrate}}}}})
            ovp.o3r.reboot()
            logger.info("Waiting for OVP to reboot...")
            time.sleep(120)
            ovp.connect()

    if time_server:
        current_timeservers = ovp.o3r.get(["/device/clock/sntp/availableServers"])["device"]["clock"]["sntp"]["availableServers"]
        if time_server not in current_timeservers:
            ovp.o3r.set({
                "device":{
                    "clock":{
                        "sntp":{
                            "active": True,
                            "availableServers": [time_server]+current_timeservers,
                        }
                    }
                }
            })

    # %%#########################################
    # Collect information about the OVP and optionally confirm the compatibility of the application to be deployed with the OVP firmware. If needed, integrate programmatic firmware update into the deployment process. Reset the OVP if needed.
    #############################################
    logger.info(f"OVP firmware version = {ovp.fw_version}")
    if update_fw is not None and firmware_version_to_use and ovp.fw_version != firmware_version_to_use:
        if firmware_image_to_use:
            update_fw(firmware_image_to_use, ovp._o3r.ip)
            ovp.connect()
        else:
            logger.error(
                f"OVP firmware version {ovp.fw_version} does not match the required version {firmware_version_to_use}")
            raise RuntimeError(
                f"OVP firmware version {ovp.fw_version} does not match the required version {firmware_version_to_use}")
    elif reset_vpu:
        reset_delay = 200
        ovp.o3r.factory_reset(keep_network_settings=True)
        logger.info(
            f"OVP reset command sent. Waiting for {reset_delay}s for OVP to reboot...")
        time.sleep(reset_delay)
        ovp.connect()

    # %%#########################################
    # Take steps to calibrate system and save those calibrations if needed. It is recommended to do this in some traceable way so that a vpu can be interchanged with another and the calibration can be optionally re-applied in the future.
    #############################################
    detect_vpu_sn = ovp.vpu_sn
    logger.info(f"OVP serial number = {detect_vpu_sn}")

    # ...
    # ... perform calibration steps here (or collect from a cached copy)
    # ...

    vpu_application_desc = "ovp_docker_test"
    vpu_instance = "---"
    vpu_name = f"{vpu_application_desc}_{vpu_instance}"

    ovp.set_vpu_name(vpu_name)

    # %%#########################################
    # Optionally remove any existing docker containers, images, and volumes
    #############################################
    loading_new_image = False
    running_containers = ovp.get_running_docker_containers()
    logger.info(f"Running containers = {running_containers}")
    ovp.remove_running_docker_containers(running_containers)
    cached_images = ovp.get_cached_docker_images()
    logger.info(f"Cached images = {cached_images}")
    if purge_docker_images_on_OVP:
        ovp.remove_cached_docker_images(cached_images)
        loading_new_image = True
    elif not replace_existing_image:
        if service_instance_params.docker_repository_name in [image["REPOSITORY"] for image in cached_images]:
            loading_new_image = False
        else:
            loading_new_image = True
    else:
        loading_new_image = True
    cached_volumes = ovp.get_registered_docker_volumes()
    logger.info(f"Cached volumes = {cached_volumes}")
    ovp.remove_registered_docker_volumes(cached_volumes)

    # %%#########################################
    # Collect logs from the OVP
    #############################################
    # add a log file collection strategy here if desired

    # %%#########################################
    # Run the mount command on the vpu to detect any usb disks
    #############################################
    usb_directories_detected = ovp.mount_usb()
    logger.info(f"{len(usb_directories_detected)} usb disk mounts detected: {usb_directories_detected}")

    # add the volume mappings to the docker-compose file
    for mount in usb_directories_detected:
        volume_mapping = f"{mount}:{mount}"
        if volume_mapping not in service_instance_params.docker_compose["services"][service_instance_params.service_name]["volumes"]:
            service_instance_params.docker_compose["services"][service_instance_params.service_name]["volumes"].append(volume_mapping)

    # %%#########################################
    # Prepare a directory on the OVP to share with the container
    #############################################
    ovp.mkdir("/home/oem/share")

    # %%#########################################
    # Setup the docker volume(s) on the OVP if needed.
    #############################################
    # it's simpler to just mount a directory when initializing a container rather than defining a volume. in the demos, we do this rather than create a docker volume and then mount the volume.
    # ovp.setup_docker_volume("/home/oem/share", "oemshare")

    # %%#########################################
    # If loading a docker image via a docker registry, setup the registry on the OVP
    #############################################
    if not tar_image_transfer:
        # get IP address of deployment PC relative to connected OVP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((ovp.config.IP, 22))
        docker_registry_host = s.getsockname()[0]
        s.close()
        logger.info(f"local docker registry host address (relative to VPU) = {docker_registry_host}")

        ovp.append_docker_registry(
            docker_registry_host=docker_registry_host,
            docker_registry_port=docker_registry_port,
            timeout = 150
        )

    # %%#########################################
    # Load the docker image onto the OVP
    #############################################
    if loading_new_image:
        if (service_instance_params.tag_to_pull_from_registry and (not tar_image_transfer)):
            ovp.pull_docker_image_from_registry(
                docker_registry_host=docker_registry_host,
                docker_registry_port=docker_registry_port,
                docker_tag=service_instance_params.tag_to_pull_from_registry,
                update_tag_on_OVP_to=service_instance_params.docker_repository_name
            )
        elif service_instance_params.docker_image_src_on_pc and service_instance_params.docker_image_dst_on_vpu and tar_image_transfer:
            logger.info(
                f"Transferring image {service_instance_params.docker_image_src_on_pc} to OVP...")
            for src, dst in [
                [service_instance_params.docker_image_src_on_pc,
                    service_instance_params.docker_image_dst_on_vpu],
            ]:
                ovp.transfer_to_vpu(src, dst)

            ovp.load_docker_image(
                image_to_load=service_instance_params.docker_image_dst_on_vpu,
                update_tag_on_OVP_to=service_instance_params.docker_repository_name
            )
            # # remove the image from the host machine if desired
            if remove_tar_file_after_loading:
                ovp.rm_item(
                    service_instance_params.docker_image_dst_on_vpu)
        else:
            logger.error("No image specified to load")

    # %#########################################
    # Fix file permissions on the OVP
    #############################################

    # run chown in docker container
    oem_id = 442
    cmd = f"chown -R {oem_id}:{oem_id} /home/oem"
    docker_cmd = f'docker run -i --volume /home/oem:/home/oem {service_instance_params.tag_to_pull_from_registry} /bin/bash -c "{cmd}"'
    logger.info(f"running {docker_cmd}")
    _stdin, _stdout, _stderr = ovp.ssh.exec_command(docker_cmd)
    stdout = _stdout.read().decode().strip()
    stderr = _stderr.read().decode().strip()
    logger.info(f"{stdout}{stderr}")


    # %%#########################################
    # Transfer files to the OVP (make sure that all directories in the path exist)
    #############################################

    with open(service_instance_params.docker_compose_src_on_pc, "w") as f:
        yaml.dump(service_instance_params.docker_compose, f)

    for src, dst in [
        [service_instance_params.docker_compose_src_on_pc,
            service_instance_params.docker_compose_dst_on_vpu],
    ]+service_instance_params.additional_project_files_to_transfer:
        ovp.transfer_to_vpu(src, dst)
    # for large directories, it may be preferred to try the SCP_sync method rather than this parameter of the service_instance_params


    # %%#########################################
    # Add additional configuration to the ovp config if desired
    #############################################

    # These tasks could include updating the baud rate on the CAN bus, setting up gateways, timeservers references, etc.
    service_components.predeployment_setup()

    # %% #########################################
    # Enable/disable autostart on the OVP if desired
    #############################################

    # find all instances of docker-compose autostart on the OVP
    enabled_docker_compose_services = ovp.get_all_autostart_instances()
    logger.info(
        f"The following docker-compose autostart instances were encountered: {enabled_docker_compose_services}")

    if disable_autostart:
        for service in enabled_docker_compose_services:
            ovp.disable_autostart(service)

    if enable_autostart:
        ovp.enable_autostart(
            service_instance_params.docker_compose_dst_on_vpu, service_instance_params.service_name)

    if ovp.autostart_enabled(service_instance_params.service_name):
        logger.info("Autostart enabled")

    # %%#########################################
    # Initialize the docker container on the OVP and get the output via stdout...
    # Note that stderr and stdout are combined in the output_from_container 
    # that the container writes to
    #############################################
    output_from_container = ovp.initialize_container(
        service=service_instance_params,
        pipe_duration=seconds_of_output,
        stop_upon_exit=False,
        autostart_enabled=enable_autostart
    )

    # %%#########################################
    # Optionally, add information to the log file dst for traceability
    #############################################
    logger.info(f"Log file path = {ovp.log_file_path}")
    container_output_path = ovp.log_file_path.replace(
        ".log", ".output.log")
    with open(container_output_path, "w") as f:
        f.write("\n".join(output_from_container))

# %%
if __name__ == "__main__" and "ipykernel" not in sys.modules:
    import typer
    from pprint import pprint

    print(notice + "Available demo services:")
    pprint(list(demo_deployment_components.keys()))
    print()
    typer.run(deploy)
# %%
