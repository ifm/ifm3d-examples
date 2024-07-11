# %%#########################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import time
import os
import sys
from pathlib import Path
import socket
from typing import List
import inspect

from ovp_docker_utils import logger, Manager, ManagerConfig, DockerComposeServiceInstance

from docker_build import docker_build, convert_nt_to_wsl

sys.path.append((Path(__file__).parent.parent/"python" /
                "ovp8xxexamples"/"core").absolute().as_posix())
from fw_update_utils import update_fw

import semver
import yaml

    
# %%#########################################
# Define some the basic structure of the docker-compose files for each deployment example
#############################################

suggested_docker_compose_parameters = {
    "version": "2.4",
}
suggested_docker_compose_service_parameters = {
    "restart": "unless-stopped",
    "environment": [
        "ON_VPU=1",
        "IFM3D_IP=172.17.0.1"
    ],
    # Rather than deploying configs by packaging them up in a container, deploy them using a directory shared between the host and the container
    "volumes": [
        "/home/oem/share/:/home/oem/share/"
    ],
    "logging":{
        "driver": "none",
    }
}




def deploy(
    service_name: str,

    reset_vpu: bool = False,

    attempt_rebuild_of_docker_image: bool = True,
    remove_all_docker_images_from_VPU_before_loading: bool = False,
    replace_image_if_already_present_on_VPU: bool = True,
    
    disable_autostart:bool = True,
    enable_autostart:bool = True,
    
    enable_std_docker_logging:bool = False,

    use_tar_file_image_transfer_rather_than_registry:bool = False,
    remove_image_tar_from_VPU_after_loading:bool = True,
    docker_registry_port: int = 5005,
    docker_registry_host_relative_to_pc: str = "localhost",
    # Note, on some systems you may need to open the port in the firewall for incoming tcp connections

    ip: str = "192.168.0.69",
    possible_initial_ip_addresses_to_try: List[str] = [],
    log_dir: str = "logs",
    
    # Path to firmware image eg: "~/ovp8xx_firmware/OVP80x_Firmware_1.1.30.1882.swu"
    firmware_image_to_use: str = "",
    firmware_version_to_use: str = "",  # Version to match eg: "1.1.30"

    seconds_of_output_to_capture: int = 60,
    ):
    """
    This script is intended to be run on a PC to deploy a
    docker image to an ovp8xx. It is recommended to understand
    each section of the script before running it. The script is
    intended to be used as a template and may need to be modified
    to suit the specific needs of an application deployment.

    Using a registry requires starting the container prior to building a container and running deployment
    `docker run -d -p <docker_registry_port>:5000 --name registry registry:latest`

    Alternatively, you can simply build a container and transfer the .tar image file.

    Args:
    reset_vpu (bool, optional): Reset the VPU before deployment. Defaults to True.

    attempt_rebuild_of_docker_image (bool, optional): Attempt to rebuild the docker image. Defaults to True.
    remove_all_docker_images_from_VPU_before_loading (bool, optional): Remove all docker images from the VPU before loading the new image. Defaults to False.
    replace_image_if_already_present_on_VPU (bool, optional): Replace the image if it is already present on the VPU. Defaults to True.

    disable_autostart (bool, optional): Disable autostart of any existing docker-compose services. Defaults to True.
    enable_autostart (bool, optional): Enable autostart of the docker-compose service being deployed. Defaults to True.

    enable_std_docker_logging (bool, optional): Enable standard docker logging. Defaults to False.
    service_name (str, optional): Name of the service to deploy from ["python", "cpp", "canopen", "ros2"]. Defaults to "" (python).

    use_tar_file_image_transfer_rather_than_registry (bool, optional): Use tar file image transfer rather than registry. Defaults to False.
    remove_image_tar_from_VPU_after_loading (bool, optional): Remove image tar from VPU after loading. Defaults to True.
    docker_registry_port (int, optional): Docker registry port. Defaults to 5005.
    docker_registry_host_relative_to_pc (str, optional): Docker registry host relative to PC. Defaults to "localhost".

    IP (str, optional): IP address of the VPU. Defaults to "192.168.0.69".
    possible_initial_ip_addresses_to_try (List[str], optional): Possible initial IP addresses to try. Defaults to [].
    log_dir (str, optional): Log directory. Defaults to "logs".
    
    firmware_image_to_use (str, optional): Path to firmware image. Defaults to "".
    firmware_version_to_use (str, optional): Firmware version to use. Defaults to "".

    seconds_of_output_to_capture (int, optional): Seconds of output to capture. Defaults to 1000.
    """

    logger.info(""" Note:
        This script is intended to be run on a PC to deploy a
        docker image to an ovp8xx. It is recommended to understand
        each section of the script before running it. The script is
        intended to be used as a template and may need to be modified
        to suit the specific needs of an application deployment.""")


    # %%#########################################
    # Set options for the deployment process
    #############################################

    # Leverage the default values of the deployment parameters if running interactively (useful for debug)
    if "ipykernel" in sys.modules:
        jupyter_notebook_args = {
            "service_name": "python"
        }
        jupyter_notebook_args.update({k:v.default
                         for k, v in inspect.signature(deploy).parameters.items() if (v.default != inspect.Parameter.empty) and (k not in locals())})
        locals().update(jupyter_notebook_args)

    manager_config = ManagerConfig(
        IP=ip,
        # If the IP above is not correct, the manager will try the additional IPs..
        # If found, the manager will change them to the specified IP
        possible_initial_ip_addresses_to_try=possible_initial_ip_addresses_to_try,
        log_dir = log_dir
    )

    # %%#########################################
    # Prepare to build the docker images if needed
    #############################################

    BUILD_DIR = Path(__file__).parent.absolute()
    os.chdir(BUILD_DIR)
    # One may or may not want to save temporary files (docker images or docker compose files) in the same directory
    tmp_dir = BUILD_DIR / "tmp"
    if not tmp_dir.exists():
        tmp_dir.mkdir()

    # %%#########################################
    # Switch to the appropriate service to prepare the deployment
    #############################################

    if service_name == "python" or not service_name:
        # DockerComposeServiceInstance( will either load the yaml file from "docker_compose_src_on_pc" for verification or will save attribute "docker-compose" to "docker_compose_dst_on_vpu" as a yaml file
        if use_tar_file_image_transfer_rather_than_registry:
            docker_image_src_on_pc = tmp_dir / "docker_python_deps.tar"
            docker_image_dst_on_vpu = "~/docker_python_deps.tar"
        else:
            docker_image_src_on_pc = ""
            docker_image_dst_on_vpu = ""
        docker_compose = {
                **suggested_docker_compose_parameters,
                "services": {
                    "example_container_python": {
                        "image": "ovp_python_deps:arm64",
                        "container_name": "example_python",
                        "entrypoint": "python3 /home/oem/share/oem_logging_example.py",
                        **suggested_docker_compose_service_parameters
                    }
                },
            }
        service_to_deploy = DockerComposeServiceInstance(
            tag_to_pull_from_registry="ovp_python_deps:arm64",
            additional_project_files_to_transfer=[
                [f"{BUILD_DIR}/python/oem_logging_example.py", "~/share/oem_logging_example.py"],
                [f"{BUILD_DIR}/python/config.json", "~/share/config.json"],
            ],
            volumes_to_setup=[("/home/oem/share", "oemshare")],
            docker_image_src_on_pc= docker_image_src_on_pc,
            docker_image_dst_on_vpu= docker_image_dst_on_vpu,
            docker_compose_src_on_pc= str(tmp_dir / "python_dc.yml"),
            docker_compose_dst_on_vpu="~/python_dc.yml",
            docker_compose= docker_compose
        )
        if attempt_rebuild_of_docker_image:
            docker_build(
                build_dir=BUILD_DIR,
                dockerfile_path=str(BUILD_DIR / "python" / "python_deps.Dockerfile"),
                repo_name="ovp_python_deps:arm64",
                docker_build_output_path= str(docker_image_src_on_pc),
                registry_host=docker_registry_host_relative_to_pc,
                registry_port=docker_registry_port
            )
    if service_name == "cpp":

        entrypoint, working_dir, build_cmd = "/home/oem/cpp/build/ods/ods_demo", "", ""
        entrypoint, working_dir, build_cmd = "/home/oem/cpp/build/core/ifm3d_playground", "", ""

        tag_base_name = "ovp_cpp"
        docker_image_src_on_pc = ""
        docker_image_dst_on_vpu = ""
        if use_tar_file_image_transfer_rather_than_registry:
            docker_image_src_on_pc = tmp_dir / "docker_cpp_build_im.tar"
            docker_image_dst_on_vpu = "~/docker_cpp_build_im.tar"
        
        service_to_deploy = DockerComposeServiceInstance(
            docker_compose_src_on_pc=f"{tmp_dir}/cpp2_dc.yml",
            docker_compose_dst_on_vpu="~/cpp2_dc.yml",
            volumes_to_setup=[("/home/oem/share", "oemshare")],
            tag_to_pull_from_registry=tag_base_name,
            docker_image_src_on_pc=docker_image_src_on_pc,
            docker_image_dst_on_vpu=docker_image_dst_on_vpu,
            docker_compose={
                **suggested_docker_compose_parameters,
                "services": {
                    "example_container_cpp": {
                        "image": tag_base_name,
                        "container_name": "example_container_cpp",
                        "working_dir": "/home/oem/cpp/build/ods",
                        "entrypoint": entrypoint,
                        **suggested_docker_compose_service_parameters
                    }
                }
            }
        )

        cpp_build_dir = BUILD_DIR.parent
        if attempt_rebuild_of_docker_image:
            docker_build(
                build_dir=cpp_build_dir,
                dockerfile_path=str(BUILD_DIR / "cpp"/ "cpp.Dockerfile"),
                repo_name=tag_base_name,
                docker_build_output_path= str(docker_image_dst_on_vpu),
                registry_host=docker_registry_host_relative_to_pc,
                registry_port=docker_registry_port,
                build_args={
                    "ARCH": "arm64",
                    "cpp_examples_path": "cpp",
                }
            )



    if service_name == "canopen":
        if use_tar_file_image_transfer_rather_than_registry:
            docker_image_src_on_pc = tmp_dir / "docker_canopen_deps.tar"
            docker_image_dst_on_vpu = "~/docker_canopen_deps.tar"
        else:
            docker_image_src_on_pc = ""
            docker_image_dst_on_vpu = ""
        docker_compose = {
                **suggested_docker_compose_parameters,
                "services": {
                    "can_example": {
                        "image": "ovp_canopen_deps:arm64",
                        "container_name": "can_example",
                        "entrypoint": "python3 /home/oem/share/can_example.py",
                        "network_mode": "host",
                        "cap_add": ["NET_ADMIN"],
                        **suggested_docker_compose_service_parameters
                    }
                },
            }
        service_to_deploy = DockerComposeServiceInstance(
            docker_compose_src_on_pc="./tmp/canopen_dc.yml",
            docker_compose_dst_on_vpu="~/canopen_dc.yml",
            additional_project_files_to_transfer=[
                [f"./{service_name}/can_example.py", "~/share/can_example.py"],
                [f"./{service_name}/config.json", "~/share/config.json"],
                [f"./{service_name}/utils", "~/share/utils"],
            ],
            volumes_to_setup=[("/home/oem/share", "oemshare")],
            tag_to_pull_from_registry="ovp_canopen_deps:arm64",
            docker_image_src_on_pc= docker_image_src_on_pc,
            docker_image_dst_on_vpu= docker_image_dst_on_vpu,
            docker_compose=docker_compose
        )
        if attempt_rebuild_of_docker_image:
            docker_build(
                build_dir=BUILD_DIR,
                dockerfile_path=str(BUILD_DIR / "canopen" / "python_deps.Dockerfile"),
                repo_name="ovp_canopen_deps:arm64",
                docker_build_output_path= str(docker_image_src_on_pc),
                registry_host=docker_registry_host_relative_to_pc,
                registry_port=docker_registry_port
            )
    if service_name == "ros2":
        if use_tar_file_image_transfer_rather_than_registry:
            docker_image_src_on_pc = tmp_dir / "ifm3d-ros-humble-arm64.tar"
            docker_image_dst_on_vpu = "~/ifm3d-ros-humble-arm64.tar"
        else:
            docker_image_src_on_pc = ""
            docker_image_dst_on_vpu = ""
        ros2_docker_compose = {
                **suggested_docker_compose_parameters,
                "services": {
                    "ros2_main": {
                        "tty": "true",
                        "ipc": "host",
                        "image": "ifm3d-ros:humble-arm64",
                        "container_name": "ros2",
                        # "entrypoint": "/bin/bash -c",
                        "entrypoint": 
                            "/bin/bash -c '"+ "; ".join(
                                [
                                    "sleep 1",
                                    "echo Setting up Ros2 environment...",
                                    "set -a",
                                    ". /opt/ros/humble/setup.sh",
                                    ". /home/ifm/colcon_ws/install/setup.sh",
                                    "export GLOG_logtostderr=1",
                                    "export GLOG_minloglevel=3",
                                    "echo ROS_DOMAIN_ID=$$ROS_DOMAIN_ID",
                                    "ros2 launch ifm3d_ros2 camera.launch.py'"
                                ]
                            )
                        ,
                        "environment": [
                            "ON_VPU=1",
                            "IFM3D_IP=172.17.0.1",
                            "ROS_DOMAIN_ID=0",
                        ],
                        "network_mode": "host",
                    }
                }
            }
        if not enable_std_docker_logging:
            ros2_docker_compose["services"]["ros2_main"]["logging"] = {
                "driver": "none"
            }
        service_to_deploy = DockerComposeServiceInstance(
            docker_compose_src_on_pc="./tmp/ros2_dc.yml",
            docker_compose_dst_on_vpu="~/ros2_dc.yml",
            volumes_to_setup=[("/home/oem/share", "oemshare")],
            additional_project_files_to_transfer=[
                ["./oem_logging_example.py", "~/share/oem_logging_example.py"],
                ["./config.json", "~/share/config.json"],
            ],
            tag_to_pull_from_registry="ifm3d-ros:humble-arm64",
            docker_image_src_on_pc= docker_image_src_on_pc,
            docker_image_dst_on_vpu= docker_image_dst_on_vpu,
            docker_compose= ros2_docker_compose
        )
        docker_compose_local_rviz ={
                **suggested_docker_compose_parameters,
                "services": {
                    "ros2_main": {
                        "tty": "true",
                        # "ipc": "host",
                        "image": "ifm3d-ros:humble-arm64",
                        "container_name": "ros2",
                        "command": [
                            "/bin/bash",
                            "-c",
                            "; ".join(
                                [
                                    "sleep 10",
                                    "echo Setting up Ros2 environment...",
                                    "set -a",
                                    ". /opt/ros/humble/setup.sh",
                                    ". /home/ifm/colcon_ws/install/setup.sh",
                                    "export GLOG_logtostderr=1",
                                    "export GLOG_minloglevel=3",
                                    "echo ROS_DOMAIN_ID=$$ROS_DOMAIN_ID",
                                    "ros2 launch ifm3d_ros2 camera.launch.py visualization:=true"
                                ]
                            )
                        ],
                        "environment": [
                            "ON_VPU=1",
                            "IFM3D_IP=172.17.0.1",
                            "ROS_DOMAIN_ID=0",
                            "QT_X11_NO_MITSHM=1"
                        ],
                        "network_mode": "host",
                        "logging" : {
                            "driver": "none"
                        }
                    }
                }
            }
        if attempt_rebuild_of_docker_image:
            docker_build(
                build_dir=BUILD_DIR,
                dockerfile_path=str(BUILD_DIR / "ros2" / "ros2.Dockerfile"),
                repo_name="ifm3d-ros:humble-arm64",
                docker_build_output_path= str(docker_image_src_on_pc),
                build_args={
                    "ARCH": "arm64",
                    "UBUNTU_VERSION": "22.04",
                    "BASE_IMAGE": "arm64v8/ros",
                    "BUILD_IMAGE_TAG": "humble",
                    "FINAL_IMAGE_TAG": "humble-ros-core",
                    "IFM3D_VERSION": "1.5.3",
                    "IFM3D_ROS2_REPO": "https://github.com/ifm/ifm3d-ros2.git",
                    "IFM3D_ROS2_BRANCH": "v1.1.0",
                },
                target = "base_dependencies",
                registry_host=docker_registry_host_relative_to_pc,
                registry_port=docker_registry_port
            )
            docker_build(
                build_dir=BUILD_DIR,
                dockerfile_path=str(BUILD_DIR / "ros2" / "ros2.Dockerfile"),
                repo_name="ifm3d-ros:humble-amd64",
                arch="amd64",
                build_args={
                    "ARCH": "amd64",
                    "UBUNTU_VERSION": "22.04",
                    "BASE_IMAGE": "osrf/ros",
                    "BUILD_IMAGE_TAG": "humble-desktop-full",
                    "FINAL_IMAGE_TAG": "humble-desktop-full",
                    "IFM3D_VERSION": "1.5.3",
                    "IFM3D_ROS2_REPO": "https://github.com/ifm/ifm3d-ros2.git",
                    "IFM3D_ROS2_BRANCH": "v1.1.0",
                },
                registry_host=docker_registry_host_relative_to_pc,
                registry_port=docker_registry_port,
            )
            # ## to enable desktop gui applications:
            # # on nt:
            # docker run -it -v /tmp/.X11-unix:/tmp/.X11-unix --env=QT_X11_NO_MITSHM=1 --net=host ifm3d-ros:humble-amd64
            # # on ubuntu:
            # docker run -d -v /tmp/.X11-unix:/tmp/.X11-unix --env=QT_X11_NO_MITSHM=1 --env=DISPLAY=:0 --net=host --name=humble ifm3d-ros:humble-amd64
            
            # docker exec -it ros2 bash -c '. /opt/ros/humble/setup.bash && rviz2'
            
            # On windows it may be necessary to fix firewall boundaries to connect with LAN for ROS2 interface
    # %%#########################################
    # Initialize the manager object
    #############################################
    manager = Manager(
        manager_config
    )

    # %%#########################################
    # Add additional configuration to the ovp config if desired
    #############################################

    # # Note that gateway must match the subnet of the interface so we'll update that per the LAN configuration.
    # new_gateway = "192.168.0.1"
    # current_gateway = manager.o3r.get()["device"]["network"]["interfaces"]["eth0"]["ipv4"]["gateway"]
    # if new_gateway != current_gateway:
    #     logger.info(f"Changing gateway from {current_gateway} to {new_gateway}")
    #     manager.o3r.set({"device": {"network": {"interfaces": {"eth0": {"ipv4": {"gateway": new_gateway}}}}}})
    #     manager.o3r.reboot()
    #     logger.info("Waiting 2 minutes for VPU to reboot...")
    #     time.sleep(120)
    #     manager.connect()

    # for some services, we need to set up the can0 interface on the VPU and reboot for it to be available
    if service_name == "canopen" and semver.compare(manager.fw_version, "1.4.0")>0:
        o3r = manager.o3r
        can_state = o3r.get()["device"]["network"]["interfaces"]["can0"]
        if can_state["active"] == False or can_state["bitrate"] != "250K":
            logger.info("Setting up can0 interface...")
            o3r.set({"device": {"network": {"interfaces": {"can0": {"active": True, "bitrate": "250K"}}}}})
            o3r.reboot()
            logger.info("Waiting for VPU to reboot...")
            time.sleep(120)
            manager.connect()

    # %%#########################################
    # Collect information about the VPU and optionally confirm the compatibility of the application to be deployed with the VPU firmware. If needed, integrate programmatic firmware update into the deployment process. Reset the VPU if needed.
    #############################################
    logger.info(f"VPU firmware version = {manager.fw_version}")
    if firmware_version_to_use and manager.fw_version != firmware_version_to_use:
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
        logger.info(f"VPU reset command sent. Waiting for {reset_delay}s for VPU to reboot...")
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
    if remove_all_docker_images_from_VPU_before_loading:
        manager.remove_cached_docker_images(cached_images)
        loading_new_image = True
    elif not replace_image_if_already_present_on_VPU:
        if service_to_deploy.docker_repository_name in [image["REPOSITORY"] for image in cached_images]:
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
    manager.get_logs(local_log_cache=f"{BUILD_DIR}/logs")

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
    for f in os.walk(BUILD_DIR/"python"):
        if "__pycache__" in f:
            os.remove(f)

    with open(service_to_deploy.docker_compose_src_on_pc, "w") as f:
        yaml.dump(service_to_deploy.docker_compose, f)
    for src, dst in [
        [service_to_deploy.docker_compose_src_on_pc, service_to_deploy.docker_compose_dst_on_vpu],
    ]+service_to_deploy.additional_project_files_to_transfer:
        manager.transfer_to_vpu(src, dst)

    # %%#########################################
    # Setup the docker volume(s) on the VPU if needed.
    #############################################
    # Bind mounts can cause issues with permissions, so it is recommended to use a docker volume
    # manager.setup_docker_volume("/home/oem/share", "oemshare")


    # %%#########################################
    # If loading a docker image via a docker registry, setup the registry on the VPU
    #############################################
    if not use_tar_file_image_transfer_rather_than_registry:
        # get IP address of deployment PC relative to connected VPU
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((manager.config.IP, 22))
        docker_registry_host = s.getsockname()[0]
        s.close()

        manager.append_docker_registry(
            docker_registry_host=docker_registry_host,
            docker_registry_port=docker_registry_port,
        )

    # %%#########################################
    # Load the docker image onto the VPU
    #############################################
    if loading_new_image:
        if (service_to_deploy.tag_to_pull_from_registry and (not use_tar_file_image_transfer_rather_than_registry)):
            manager.pull_docker_image_from_registry(
                docker_registry_host=docker_registry_host,
                docker_registry_port=docker_registry_port,
                docker_tag=service_to_deploy.tag_to_pull_from_registry,
                update_tag_on_VPU_to=service_to_deploy.docker_repository_name
            )
        elif service_to_deploy.docker_image_src_on_pc and service_to_deploy.docker_image_dst_on_vpu and use_tar_file_image_transfer_rather_than_registry:
            logger.info(
                f"Transferring image {service_to_deploy.docker_image_src_on_pc} to VPU...")
            for src, dst in [
                [service_to_deploy.docker_image_src_on_pc,
                    service_to_deploy.docker_image_dst_on_vpu],
            ]:
                manager.transfer_to_vpu(src, dst)

            manager.load_docker_image(
                image_to_load=service_to_deploy.docker_image_dst_on_vpu,
                update_tag_on_VPU_to=service_to_deploy.docker_repository_name
            )
            # # remove the image from the host machine if desired
            if remove_image_tar_from_VPU_after_loading:
                manager.rm_item(service_to_deploy.docker_image_dst_on_vpu)
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
            service_to_deploy.docker_compose_dst_on_vpu, service_to_deploy.service_name)

    if manager.autostart_enabled(service_to_deploy.service_name):
        logger.info("Autostart enabled")

    # %%#########################################
    # Initialize the docker container on the VPU and get the output via stdout...
    # Note that stderr is not captured by this library, for this you will need to
    # attach to the container via the console using ssh or review some log file
    # that the container writes to
    #############################################
    output_from_container = manager.initialize_container(
        service=service_to_deploy,
        pipe_duration=seconds_of_output_to_capture,
        stop_upon_exit=False,
        autostart_enabled = enable_autostart
    )

    # %%#########################################
    # Optionally, add information to the log file dst for traceability
    #############################################
    logger.info(f"Log file path = {manager.log_file_path}")
    container_output_path = manager.log_file_path.replace(".log", ".output.log")
    with open(container_output_path, "w") as f:
        f.write("\n".join(output_from_container))
    # %%#########################################
    # When things go wrong, the in-memory journal from the VPU can be helpful for debug
    #############################################

    # manager.pull_journalctl_logs(dst_dir=Path(__file__).parent)

# %%
import sys
if __name__ == "__main__" and "ipykernel" not in sys.modules:
    import typer
    typer.run(deploy)
# %%
