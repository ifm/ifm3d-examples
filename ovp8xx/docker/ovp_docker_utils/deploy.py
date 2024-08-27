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

sys.path.append((Path(__file__).parent.parent).absolute().as_posix())
from ovp_docker_utils.ovp_handle import logger, OVPHandle, OVPHandleConfig
from ovp_docker_utils.docker_compose_instance import DockerComposeServiceInstance
from ovp_docker_utils.ssh_file_utils import SCP_synctree, SCP_transfer_item
from ovp_docker_utils.deployment_components import DeploymentComponents,demo_deployment_components
from ovp_docker_utils.remote import download_if_unavailable, uncompress_bz2
from ovp_docker_utils.deployment_components import ImageSource
from ovp_docker_utils.docker_cli import save_docker_image, load_docker_image, push_docker_image, pull_docker_image
from ovp_docker_utils.docker_cli import parse_docker_table_output
from ovp_docker_utils.cli import cli_tee
from ovp_docker_utils.ssh_pipe import ssh_pipe


sys.path.append((Path(__file__).parent.parent.parent/"python" /
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
    dusty_nv_packages: str = "", # comma separated list of dusty nv packages to install
    purge_docker_images_on_OVP: bool = False,

    disable_autostart: bool = True,
    enable_autostart: bool = True,

    docker_registry_port: int = 5005,
    docker_registry_host_relative_to_pc: str = "localhost",

    # new parameters
    image_delivery_mode: str = "local-tar",
    pc_image_aquisition_mode: str = "build-packages",


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

    assert image_delivery_mode in ["local-tar", "local-registry", "remote-registry", "remote-tar"], "Invalid image delivery mode"
    assert pc_image_aquisition_mode in ["build", "build-packages", "remote-registry", "remote-tar"], "Invalid PC image aquisition mode"

    packages: list = [package.strip() for package in dusty_nv_packages.split(",")]

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
    # get the UID and GID of the oem user on the OVP
    #############################################
    oem_uid, oem_gid = ovp.get_oem_uid_gid()


    # %%#########################################
    # Switch to the appropriate service to prepare the deployment
    #############################################

    if type(additional_deployment_components) == dict:
        demo_deployment_components.update(additional_deployment_components)

    # provide local variables to the deployment components
    service_components: DeploymentComponents = demo_deployment_components[service_name](
        **locals())
    service_instance_params: DockerComposeServiceInstance = service_components.docker_compose_service_instance()


    # %%#########################################
    # Build the docker image and prep for transfer if needed
    #############################################
    def tar_fname(tag,id):
        return f"{tag.replace(':','.')}.{id}.tar"
    
    if "local" in image_delivery_mode:
        if not docker_rebuild:
            image_source = ImageSource(tag = service_instance_params.tag_to_run)
        elif docker_rebuild:
            if pc_image_aquisition_mode == "build-packages":
                image_source: ImageSource = service_components.build_packages()
            elif pc_image_aquisition_mode == "build":
                image_source: ImageSource = service_components.build()
        if pc_image_aquisition_mode == "remote-registry":
            assert service_instance_params.cloud_host_tag, "tag_to_run must be set in order to deploy via remote registry"
            output = pull_docker_image(
                tag=service_instance_params.tag_to_run
            )
            image_source: ImageSource = service_instance_params.cloud_host_tag
        elif pc_image_aquisition_mode == "remote-tar":
            assert service_instance_params.remote_tar
            destination = (Path(tmp_dir) / tar_fname(service_instance_params.tag_to_run,service_instance_params.remote_tar.id)).as_posix()
            output = download_if_unavailable(
                url=service_instance_params.remote_tar.url,
                dl_path=destination,
                sha_256=service_instance_params.remote_tar.sha_256
            )
            if output:
                image_source = ImageSource(
                    tar_path=output,
                    id = service_instance_params.remote_tar.id
                )
            else:
                raise RuntimeError(f"Failed to download the image from {service_instance_params.remote_tar.url}")
        
        # get the image id
        if image_source.tag and not image_source.id:
            cmd = f"docker images"
            r, o, e = cli_tee(
                cmd,
                wsl=True,
                show_e=False,
                show_o=False,
            )
            image_list = parse_docker_table_output(o.decode().split("\n"))

            tag_match = [image["IMAGE ID"] for image in image_list if image["REPOSITORY"]+":"+image["TAG"] == image_source.tag]
            if tag_match:
                image_source.id = tag_match[0]
            else:
                raise RuntimeError(f"Image with tag {image_source.tag} not found on the PC")

        # prep for transfer
        if  image_delivery_mode == "local-tar":
            if image_source.tar_path:
                pass
            elif image_source.tag:
                image_source.tar_path = (Path(tmp_dir) / tar_fname(service_instance_params.tag_to_run, image_source.id)).as_posix()
                if not os.path.exists(image_source.tar_path):
                    save_docker_image(
                        tag=image_source.tag,
                        docker_build_output_path=image_source.tar_path
                    )
                else:
                    logger.info(f"Image already saved locally at {image_source.tar_path}. Skipping step.")
            else:
                raise RuntimeError("No image source found")
        elif image_delivery_mode == "local-registry":
            # push the image to the local registry
            if image_source.tar_path and not image_source.tag:
                # load the image from the tar file
                image_source.tag = service_instance_params.tag_to_run

                #TODO check if the image already available in cache as hosted .tar files are not updated once uploaded.
                load_docker_image(
                    tar_path=image_source.tar_path,
                    tag=image_source.tag
                )

            if image_source.tag:

                assert bool(docker_registry_host_relative_to_pc), "docker_registry_host_relative_to_pc must be set in order to deploy via local registry"
                push_docker_image(
                    tag=image_source.tag,
                    registry_host=docker_registry_host_relative_to_pc,
                    registry_port= docker_registry_port
                )
            else:
                raise RuntimeError("No image source found")


    # %%#########################################
    # configure persistent network settings
    #############################################

    if can_bitrate:
        can_state = ovp.o3r.get()["ovp"]["network"]["interfaces"]["can0"]
        if can_state["active"] == False or can_state["bitrate"] != can_bitrate:
            logger.info("Setting up can0 interface...")
            ovp.o3r.set({"ovp": {"network": {"interfaces": {
                    "can0": {"active": True, "bitrate": can_bitrate}}}}})
            ovp.o3r.reboot()
            logger.info("Waiting for OVP to reboot...")
            time.sleep(160)
            ovp.connect()

    if time_server:
        ovp.add_timeserver(time_server)

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
    # Optionally remove any existing docker containers and images
    #############################################
    
    running_containers = ovp.get_running_docker_containers()
    logger.info(f"Running containers = {running_containers}")
    ovp.remove_running_docker_containers(running_containers)
    cached_images = ovp.get_cached_docker_images()
    logger.info(f"Cached images = {cached_images}")
    image_on_vpu= image_source.id in cached_images
    if purge_docker_images_on_OVP:
        ovp.remove_cached_docker_images([im for im in cached_images if im!=image_source.id])
        loading_new_image = True
       
    loading_new_image = True

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
    # If loading a docker image via a docker registry, setup the registry on the OVP
    #############################################
    if image_delivery_mode == "local-registry":
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

    if image_on_vpu:
        logger.info("Image is already loaded onto VPU! Skipping step.")
    elif image_delivery_mode == "local-tar":
        # check if the image id is available on the device
        
        # if image_source.id and (service_instance_params.remote_tar.id in [image["IMAGE ID"] for image in ovp.get_cached_docker_images()]):
        #     logger.info("Image is already loaded onto VPU! Skipping step.")
        # else:
        docker_image_src_on_pc = image_source.tar_path


        # docker_image_dst_on_vpu = service_instance_params.tmp_dir_on_vpu+f"/{service_instance_params.tag_to_run.replace(':','.')}.tar"

        # logger.info(f"Transferring image {docker_image_src_on_pc} to OVP...")
        # ovp.transfer_to_vpu(docker_image_src_on_pc, docker_image_dst_on_vpu)
        # ovp.load_docker_image(
        #     image_to_load=docker_image_dst_on_vpu,
        #     update_tag_on_OVP_to=service_instance_params.tag_to_run
        # )
        # ovp.rm_item(docker_image_dst_on_vpu)
        logger.info(
            f"Image size = {Path(docker_image_src_on_pc).stat().st_size/1e6:.2f} MB")
        logger.info(f"Loading image {docker_image_src_on_pc} to OVP... loading may take a moment once transferred.")
        ssh_pipe(
            src=docker_image_src_on_pc,
            output_cmd=f"docker load",
            host=ovp.config.IP,
            key=ovp.config.ssh_key_dir+"/"+ovp.config.ssh_key_file_name
        )


    elif image_delivery_mode == "local-registry":
        ovp.pull_docker_image_from_registry(
            docker_registry_host=docker_registry_host,
            docker_registry_port=docker_registry_port,
            docker_tag=service_instance_params.tag_to_run,
            update_tag_on_OVP_to=service_instance_params.tag_to_run
        )
    elif image_delivery_mode == "remote-registry":
        raise NotImplementedError("remote-registry mode not implemented")
    elif image_delivery_mode == "remote-tar":
        raise NotImplementedError("remote-tar mode not implemented")

    # %#########################################
    # Fix file permissions on the OVP
    #############################################
    # If you run a container as root, files written by the container will not be accessible via ssh as oem user, therefore, you may need to run chown -R in a container to fix the permissions as shown below:

    ovp.fix_file_permissions(service_instance_params.tag_to_run, oem_uid, oem_gid)



    # %%#########################################
    # Transfer files to the OVP
    #############################################
   

    docker_compose_fname = f"{service_name}_dc.yml"
    docker_compose_on_pc = (Path(tmp_dir)/docker_compose_fname).as_posix()
    docker_compose_dst_on_vpu = (Path(service_instance_params.tmp_dir_on_vpu) / docker_compose_fname).as_posix()
    with open(docker_compose_on_pc, "w") as f:
        yaml.dump(service_instance_params.docker_compose, f)
    SCP_transfer_item(
        ssh=ovp.ssh,
        scp=ovp.scp,
        src=docker_compose_on_pc,
        dst=docker_compose_dst_on_vpu,
    )

    for mapping in service_instance_params.file_system_mappings:
        SCP_synctree(
            ssh=ovp.ssh,
            scp=ovp.scp,
            src=mapping.src,
            dst=mapping.dst,
            src_is_local=True,
            exclude_regex=mapping.exclude_regex,
            verbose = True
        )



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
        ovp.enable_autostart(docker_compose_dst_on_vpu, service_instance_params.service_name)

    if ovp.autostart_enabled(service_instance_params.service_name):
        logger.info("Autostart enabled")

    # %%#########################################
    # Initialize the docker container on the OVP and get the output via stdout...
    # Note that stderr and stdout are combined in the output_from_container 
    # that the container writes to
    #############################################
    output_from_container = ovp.initialize_container(
        # service=service_instance_params,
        service_name= service_instance_params.service_name,
        docker_compose_dst = service_instance_params.tmp_dir_on_vpu,
        container_name = service_instance_params.container_name,
        service_log_driver = service_instance_params.log_driver, 

        pipe_duration=seconds_of_output,
        stop_upon_exit=False,
        autostart_enabled=enable_autostart
    )

    # %%#########################################
    # Optionally, add information to the log file dst for traceability
    #############################################
    return output_from_container

# %%
if __name__ == "__main__" and "ipykernel" not in sys.modules:
    import typer
    from pprint import pprint

    print(notice + "Available demo services:")
    pprint(list(demo_deployment_components.keys()))
    print()
    typer.run(deploy)
# %%
