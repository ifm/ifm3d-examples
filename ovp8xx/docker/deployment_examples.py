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

import semver
import yaml

from ovp_docker_utils import logger, Manager, ManagerConfig, DockerComposeServiceInstance

from docker_build import docker_build, convert_nt_to_wsl
from deployment_components import DeploymentComponents,demo_deployment_components

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

DEFAULT_SECONDS_OF_OUTPUT_TO_CAPTURE = 10
DEFAULT_BUILD_DIR = Path(__file__).parent.absolute()
DEFAULT_IP = os.environ.get("IFM3D_IP", "192.168.0.69")

# %%#########################################
# Define the deployment function
#############################################

def deploy(
    service_name: str,

    reset_vpu: bool = False,

    docker_rebuild: bool = True,
    purge_docker_images_on_VPU: bool = False,
    replace_existing_image: bool = True,

    disable_autostart: bool = True,
    enable_autostart: bool = True,

    tar_image_transfer: bool = True,
    remove_tar_file_after_loading: bool = True,

    docker_registry_port: int = 5005,
    docker_registry_host_relative_to_pc: str = "localhost",

    docker_build_dir: str = str(DEFAULT_BUILD_DIR),
    tmp_dir: str = str(DEFAULT_BUILD_DIR / "tmp"),

    ip: str = DEFAULT_IP,
    possible_initial_ip_addresses_to_try: List[str] = [],
    gateway: str = "",
    netmask: int = 24,
    time_server: str = "",
    log_dir: str = "logs",

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

    reset_vpu (bool, optional): Reset the VPU before deployment. Defaults to True.

    docker_rebuild (bool, optional): Rebuild the docker image. Defaults to True.
    purge_docker_images_on_VPU (bool, optional): Purge docker images on the VPU. Defaults to False.
    replace_existing_image (bool, optional): Replace existing image. Defaults to True.

    disable_autostart (bool, optional): Disable autostart of any existing docker-compose services. Defaults to True.
    enable_autostart (bool, optional): Enable autostart of the docker-compose service being deployed. Defaults to True.

    tar_image_transfer (bool, optional): Use tar file image transfer. Defaults to True.
    remove_tar_file_after_loading (bool, optional): Remove tar file after loading. Defaults to True.

    docker_registry_port (int, optional): Docker registry port. Defaults to 5005.
    docker_registry_host_relative_to_pc (str, optional): Docker registry host relative to PC. Defaults to "localhost".

    build_dir (str, optional): Build directory. Defaults to DEFAULT_BUILD_DIR.
    tmp_dir (str, optional): Temporary directory. Defaults to DEFAULT_BUILD_DIR / "tmp".

    IP (str, optional): IP address of the VPU. Defaults to {DEFAULT_IP}.
    possible_initial_ip_addresses_to_try (List[str], optional): Possible initial IP addresses to try. Defaults to [].
    gateway (str, optional): Gateway address. Defaults to "".
    netmask (int, optional): Netmask. Defaults to 24.
    time_server (str, optional): Time server address. Defaults to "".
    log_dir (str, optional): Log directory. Defaults to "logs".

    firmware_image_to_use (str, optional): Path to firmware image. Defaults to "".
    firmware_version_to_use (str, optional): Version to match. Defaults to "".

    seconds_of_output (int, optional): Seconds of output to capture from container. Defaults to {DEFAULT_SECONDS_OF_OUTPUT_TO_CAPTURE}.

    additional_deployment_components (bool, optional): Inaccessible via CLI, but can be used to extend the demo_deployment_components. Defaults to False.


    """

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

    os.chdir(docker_build_dir)
    if not os.path.exists(tmp_dir):
        os.mkdir(tmp_dir)

    # %%#########################################
    # Switch to the appropriate service to prepare the deployment
    #############################################

    if type(additional_deployment_components) == dict:
        demo_deployment_components.update(additional_deployment_components)

    service_components: DeploymentComponents = demo_deployment_components[service_name](
        **locals())
    service_instance_params = service_components.docker_compose_service_instance()

    if docker_rebuild:
        service_components.docker_build_step()

    # %%#########################################
    # Initialize the manager object
    #############################################
    manager = Manager(
        ManagerConfig(
            IP=ip,
            possible_initial_ip_addresses_to_try=possible_initial_ip_addresses_to_try,
            gateway=gateway,
            netmask=netmask,
            log_dir=log_dir,
            ssh_key_file_name="id_rsa_ovp8xx",
        )
    )

    # %%#########################################
    # Add additional configuration to the ovp config if desired
    #############################################

    # These tasks could include updating the baud rate on the CAN bus, setting up gateways, timeservers references, etc.
    service_components.predeployment_setup(manager)

    if time_server:
        current_timeservers = manager.o3r.get(["/device/clock/sntp/availableServers"])["device"]["clock"]["sntp"]["availableServers"]
        if time_server not in current_timeservers:
            manager.o3r.set({
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
    # Collect information about the VPU and optionally confirm the compatibility of the application to be deployed with the VPU firmware. If needed, integrate programmatic firmware update into the deployment process. Reset the VPU if needed.
    #############################################
    logger.info(f"VPU firmware version = {manager.fw_version}")
    if update_fw is not None and firmware_version_to_use and manager.fw_version != firmware_version_to_use:
        if firmware_image_to_use:
            update_fw(firmware_image_to_use, manager._o3r.ip)
            manager.connect()
        else:
            logger.error(
                f"VPU firmware version {manager.fw_version} does not match the required version {firmware_version_to_use}")
            raise RuntimeError(
                f"VPU firmware version {manager.fw_version} does not match the required version {firmware_version_to_use}")
    elif reset_vpu:
        reset_delay = 200
        manager.o3r.factory_reset(keep_network_settings=True)
        logger.info(
            f"VPU reset command sent. Waiting for {reset_delay}s for VPU to reboot...")
        time.sleep(reset_delay)
        manager.connect()

    # %%#########################################
    # Take steps to calibrate system and save those calibrations if needed. It is recommended to do this in some traceable way so that a vpu can be interchanged with another and the calibration can be optionally re-applied in the future.
    #############################################
    detect_vpu_sn = manager.vpu_sn
    logger.info(f"VPU serial number = {detect_vpu_sn}")

    # ...
    # ... perform calibration steps here (or collect from a cached copy)
    # ...

    vpu_application_desc = "ovp_docker_test"
    vpu_instance = "---"
    vpu_name = f"{vpu_application_desc}_{vpu_instance}"

    manager.set_vpu_name(vpu_name)

    # %%#########################################
    # Optionally remove any existing docker containers, images, and volumes
    #############################################
    loading_new_image = False
    running_containers = manager.get_running_docker_containers()
    logger.info(f"Running containers = {running_containers}")
    manager.remove_running_docker_containers(running_containers)
    cached_images = manager.get_cached_docker_images()
    logger.info(f"Cached images = {cached_images}")
    if purge_docker_images_on_VPU:
        manager.remove_cached_docker_images(cached_images)
        loading_new_image = True
    elif not replace_existing_image:
        if service_instance_params.docker_repository_name in [image["REPOSITORY"] for image in cached_images]:
            loading_new_image = False
        else:
            loading_new_image = True
    else:
        loading_new_image = True
    cached_volumes = manager.get_registered_docker_volumes()
    logger.info(f"Cached volumes = {cached_volumes}")
    manager.remove_registered_docker_volumes(cached_volumes)

    # %%#########################################
    # Collect logs from the VPU
    #############################################
    manager.get_logs(local_log_cache=f"{docker_build_dir}/logs")

    # %%#########################################
    # Run the mount command on the vpu to detect any usb disks
    #############################################
    usb_directories_detected = manager.mount_usb()
    if usb_directories_detected:
        logger.info(f"usb disk mount detected: {usb_directories_detected}")

    # %%#########################################
    # Prepare a directory on the VPU to share with the container
    #############################################
    manager.mkdir("/home/oem/share")

    # %%#########################################
    # Transfer files to the VPU (make sure that all directories in the path exist)
    #############################################

    # some files like __pycache__ may cause permission errors in transfer if an active application is using them on the VPU, so we'll remove them
    for f in os.walk(Path(docker_build_dir)/"python"):
        if "__pycache__" in f:
            os.remove(f)

    with open(service_instance_params.docker_compose_src_on_pc, "w") as f:
        yaml.dump(service_instance_params.docker_compose, f)
    for src, dst in [
        [service_instance_params.docker_compose_src_on_pc,
            service_instance_params.docker_compose_dst_on_vpu],
    ]+service_instance_params.additional_project_files_to_transfer:
        manager.transfer_to_vpu(src, dst)

    # %%#########################################
    # Setup the docker volume(s) on the VPU if needed.
    #############################################
    # it's simpler to just mount a directory when initializing a container rather than defining a volume. in the demos, we do this rather than create a docker volume and then mount the volume.
    # manager.setup_docker_volume("/home/oem/share", "oemshare")

    # %%#########################################
    # If loading a docker image via a docker registry, setup the registry on the VPU
    #############################################
    if not tar_image_transfer:
        # get IP address of deployment PC relative to connected VPU
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((manager.config.IP, 22))
        docker_registry_host = s.getsockname()[0]
        s.close()

        manager.append_docker_registry(
            docker_registry_host=docker_registry_host,
            docker_registry_port=docker_registry_port,
            timeout = 150
        )

    # %%#########################################
    # Load the docker image onto the VPU
    #############################################
    if loading_new_image:
        if (service_instance_params.tag_to_pull_from_registry and (not tar_image_transfer)):
            manager.pull_docker_image_from_registry(
                docker_registry_host=docker_registry_host,
                docker_registry_port=docker_registry_port,
                docker_tag=service_instance_params.tag_to_pull_from_registry,
                update_tag_on_VPU_to=service_instance_params.docker_repository_name
            )
        elif service_instance_params.docker_image_src_on_pc and service_instance_params.docker_image_dst_on_vpu and tar_image_transfer:
            logger.info(
                f"Transferring image {service_instance_params.docker_image_src_on_pc} to VPU...")
            for src, dst in [
                [service_instance_params.docker_image_src_on_pc,
                    service_instance_params.docker_image_dst_on_vpu],
            ]:
                manager.transfer_to_vpu(src, dst)

            manager.load_docker_image(
                image_to_load=service_instance_params.docker_image_dst_on_vpu,
                update_tag_on_VPU_to=service_instance_params.docker_repository_name
            )
            # # remove the image from the host machine if desired
            if remove_tar_file_after_loading:
                manager.rm_item(
                    service_instance_params.docker_image_dst_on_vpu)
        else:
            logger.error("No image specified to load")

    # %% #########################################
    # Enable/disable autostart on the VPU if desired
    #############################################

    # find all instances of docker-compose autostart on the VPU
    enabled_docker_compose_services = manager.get_all_autostart_instances()
    logger.info(
        f"The following docker-compose autostart instances were encountered: {enabled_docker_compose_services}")

    if disable_autostart:
        for service in enabled_docker_compose_services:
            manager.disable_autostart(service)

    if enable_autostart:
        manager.enable_autostart(
            service_instance_params.docker_compose_dst_on_vpu, service_instance_params.service_name)

    if manager.autostart_enabled(service_instance_params.service_name):
        logger.info("Autostart enabled")

    # %%#########################################
    # Initialize the docker container on the VPU and get the output via stdout...
    # Note that stderr is not captured by this library, for this you will need to
    # attach to the container via the console using ssh or review some log file
    # that the container writes to
    #############################################
    output_from_container = manager.initialize_container(
        service=service_instance_params,
        pipe_duration=seconds_of_output,
        stop_upon_exit=False,
        autostart_enabled=enable_autostart
    )

    # %%#########################################
    # Optionally, add information to the log file dst for traceability
    #############################################
    logger.info(f"Log file path = {manager.log_file_path}")
    container_output_path = manager.log_file_path.replace(
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
