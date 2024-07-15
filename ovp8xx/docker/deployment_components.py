# %%#########################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# This file contains the deployment components for the various demo services that can be deployed on the VPU

import os
import time
from pathlib import Path

from docker_build import docker_build

from ovp_docker_utils import Manager, logger, DockerComposeServiceInstance

# %%#########################################
# Define typical structure of the docker-compose files which are used to define how the VPU runs the docker containers
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

    # The following line is used to pin the container to specific cores. This is useful if you want to ensure that the container does not interfere with the real-time performance of other applications running on the VPU (eg. the Obstacle Detection System)
    "cpuset": "0,3,4,5",

    # Rather than deploying configs or python applications by packaging them up in a container, you may prefer to deploy them using a directory shared between the host and the container
    "volumes": [
        "/home/oem/share/:/home/oem/share/"
    ],
    "logging": {
        "driver": "none",
    }
}

# %%#########################################
# Define the deployment components for the various services
#############################################

class DeploymentComponents:
    def __init__(self, **deploy_context):
        self.deploy_context = deploy_context

    def docker_compose_service_instance() -> DockerComposeServiceInstance:
        return None

    def docker_build_step(self) -> None:
        pass

    def predeployment_setup(self, manager: Manager) -> None:
        pass


demo_deployment_components = {}


class PythonDemoDeploymentComponents(DeploymentComponents):
    def __init__(
        self,
        **deploy_context
    ):
        self.deploy_context = deploy_context

        if self.deploy_context["tar_image_transfer"]:
            self.docker_image_src_on_pc = self.deploy_context["tmp_dir"] + \
                "/docker_python_deps.tar"
            self.docker_image_dst_on_vpu = "~/docker_python_deps.tar"
        else:
            self.docker_image_src_on_pc = ""
            self.docker_image_dst_on_vpu = ""

    def docker_compose_service_instance(self) -> DockerComposeServiceInstance:
        docker_build_dir = self.deploy_context["docker_build_dir"]
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

        return DockerComposeServiceInstance(
            tag_to_pull_from_registry="ovp_python_deps:arm64",
            additional_project_files_to_transfer=[
                [f"{docker_build_dir}/python/oem_logging_example.py",
                    "~/share/oem_logging_example.py"],
                [f"{docker_build_dir}/python/config.json", "~/share/config.json"],
            ],
            volumes_to_setup=[("/home/oem/share", "oemshare")],
            docker_image_src_on_pc=self.docker_image_src_on_pc,
            docker_image_dst_on_vpu=self.docker_image_dst_on_vpu,
            docker_compose_src_on_pc=self.deploy_context["tmp_dir"] +
            "/python_dc.yml",
            docker_compose_dst_on_vpu="~/python_dc.yml",
            docker_compose=docker_compose
        )

    def docker_build_step(self):
        docker_build_dir = self.deploy_context["docker_build_dir"]
        docker_build(
            build_dir=docker_build_dir,
            dockerfile_path=f"{docker_build_dir}/python/python_deps.Dockerfile",
            repo_name="ovp_python_deps:arm64",
            docker_build_output_path=self.docker_image_src_on_pc,
            registry_host=self.deploy_context['docker_registry_host_relative_to_pc'],
            registry_port=self.deploy_context['docker_registry_port']
        )

    def predeployment_setup(self, *args, **kwargs):
        pass


demo_deployment_components["python"] = PythonDemoDeploymentComponents


class CppDemoDeploymentComponents(DeploymentComponents):
    def __init__(
        self,
        build_target: str,
        executable: str,
        **deploy_context
    ):
        self.build_target = build_target
        self.executable = executable

        self.deploy_context = deploy_context

        self.tag = f"ovp_cpp_{build_target}:latest"

        if self.deploy_context["tar_image_transfer"]:
            self.docker_image_src_on_pc = f"{self.deploy_context['tmp_dir']}/docker_cpp_build_im.tar"
            self.docker_image_dst_on_vpu = "~/docker_cpp_build_im.tar"
        else:
            self.docker_image_src_on_pc = ""
            self.docker_image_dst_on_vpu = ""

    def docker_compose_service_instance(self):
        if self.build_target == "core_examples":
            working_dir = "/home/oem/cpp/core/build/"
            entrypoint = f'/bin/bash -c "sleep 3 && /home/oem/cpp/core/build/{self.executable}"'
        elif self.build_target == "ods_example_build":
            working_dir = "/home/oem/cpp/ods/build"
            entrypoint = f'/bin/bash -c "sleep 3 && /home/oem/cpp/ods/build/{self.executable}"'
        else:
            raise ValueError(
                f"Invalid target {self.build_target}. Must be 'core_examples' or 'ods_example_build'")
        docker_compose = {
            **suggested_docker_compose_parameters,
            "services": {
                "example_container_cpp": {
                    "image": self.tag,
                    "container_name": "example_container_cpp",
                    "working_dir": working_dir,
                    "entrypoint": entrypoint,
                    **suggested_docker_compose_service_parameters
                }
            },
        }
        return DockerComposeServiceInstance(
            docker_compose_src_on_pc=self.deploy_context["tmp_dir"] +
            "/cpp_dc.yml",
            docker_compose_dst_on_vpu="~/cpp_dc.yml",
            tag_to_pull_from_registry=self.tag,
            docker_image_src_on_pc=self.docker_image_src_on_pc,
            docker_image_dst_on_vpu=self.docker_image_dst_on_vpu,
            docker_compose=docker_compose
        )

    def docker_build_step(self):
        cpp_build_dir = Path(self.deploy_context["docker_build_dir"]).parent
        docker_build(
            build_dir=str(cpp_build_dir),
            dockerfile_path=f"{self.deploy_context['docker_build_dir']}/cpp/cpp.Dockerfile",
            repo_name=self.tag,
            docker_build_output_path=str(self.docker_image_src_on_pc),
            registry_host=self.deploy_context["docker_registry_host_relative_to_pc"],
            registry_port=self.deploy_context["docker_registry_port"],
            build_args={
                "ARCH": "arm64",
                "cpp_examples_path": "cpp",
                "IFM3D_VERSION": "1.5.3"
            },
            Additional_build_params=f" --target {self.build_target} "
        )

    def predeployment_setup(self, *args, **kwargs):
        pass

cpp_core_example_executables = [
    "multi_head",
    "diagnostic",
    "deserialize_rgb",
    "getting_data",
    "getting_data_callback",
    "bootup_monitor",
    "configuration",
]
# use lambda to generate anonomous functions to pass arguments to the class constructor
for executable in cpp_core_example_executables:
    demo_deployment_components["cpp_"+executable] = lambda executable = executable,**deploy_context: CppDemoDeploymentComponents(
        build_target="core_examples", executable=executable, **deploy_context)
for executable in ["ods_demo", "ods_get_data"]:
    demo_deployment_components[executable] = lambda **deploy_context: CppDemoDeploymentComponents(
        build_target="ods_example_build", executable=str(executable),**deploy_context)


OVP8XX_CAN_BAUDRATE = os.environ.get("OVP8XX_CAN_BAUDRATE", "250K")

class CanOpenDemoDeploymentComponents(DeploymentComponents):
    def __init__(
        self,
        **deploy_context
    ):
        self.deploy_context = deploy_context
        self.service_name = "canopen"

        if self.deploy_context["tar_image_transfer"]:
            self.docker_image_src_on_pc = (
                Path(self.deploy_context["tmp_dir"]) / "docker_canopen_deps.tar").as_posix()
            self.docker_image_dst_on_vpu = "~/docker_canopen_deps.tar"
        else:
            self.docker_image_src_on_pc = ""
            self.docker_image_dst_on_vpu = ""

    def docker_compose_service_instance(self):
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
        return DockerComposeServiceInstance(
            docker_compose_src_on_pc="./tmp/canopen_dc.yml",
            docker_compose_dst_on_vpu="~/canopen_dc.yml",
            additional_project_files_to_transfer=[
                [f"./{self.service_name}/can_example.py",
                    "~/share/can_example.py"],
                [f"./{self.service_name}/config.json", "~/share/config.json"],
                [f"./{self.service_name}/utils", "~/share/utils"],
            ],
            volumes_to_setup=[("/home/oem/share", "oemshare")],
            tag_to_pull_from_registry="ovp_canopen_deps:arm64",
            docker_image_src_on_pc=self.docker_image_src_on_pc,
            docker_image_dst_on_vpu=self.docker_image_dst_on_vpu,
            docker_compose=docker_compose
        )

    def docker_build_step(self):
        docker_build(
            build_dir=self.deploy_context["docker_build_dir"],
            dockerfile_path=str(Path(
                self.deploy_context["docker_build_dir"]) / "canopen" / "python_deps.Dockerfile"),
            repo_name="ovp_canopen_deps:arm64",
            docker_build_output_path=str(self.docker_image_src_on_pc),
            registry_host=self.deploy_context["docker_registry_host_relative_to_pc"],
            registry_port=self.deploy_context["docker_registry_port"]
        )

    def predeployment_setup(self, manager):
        o3r = manager.o3r
        can_state = o3r.get()["device"]["network"]["interfaces"]["can0"]
        if can_state["active"] == False or can_state["bitrate"] != OVP8XX_CAN_BAUDRATE:
            logger.info("Setting up can0 interface...")
            o3r.set({"device": {"network": {"interfaces": {
                    "can0": {"active": True, "bitrate": OVP8XX_CAN_BAUDRATE}}}}})
            o3r.reboot()
            logger.info("Waiting for VPU to reboot...")
            time.sleep(120)
            manager.connect()


demo_deployment_components["canopen"] = CanOpenDemoDeploymentComponents


class Ros2DemoDeploymentComponents(DeploymentComponents):
    def __init__(
        self,
        **deploy_context
    ):
        self.deploy_context = deploy_context
        self.service_name = "ros2"

        if self.deploy_context["tar_image_transfer"]:
            self.docker_image_src_on_pc = (
                Path(self.deploy_context["tmp_dir"]) / "ifm3d-ros-humble-arm64.tar").as_posix()
            self.docker_image_dst_on_vpu = "~/ifm3d-ros-humble-arm64.tar"
        else:
            self.docker_image_src_on_pc = ""
            self.docker_image_dst_on_vpu = ""

    def docker_compose_service_instance(self):
        ros2_docker_compose = {
            **suggested_docker_compose_parameters,
            "services": {
                "ros2_main": {
                    "tty": "true",
                    "ipc": "host",
                    "image": "ifm3d-ros:humble-arm64",
                    "container_name": "ros2",
                    "entrypoint":
                    "/bin/bash -c '" + "; ".join(
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
                    ),
                        "environment": [
                            "ON_VPU=1",
                            "IFM3D_IP=172.17.0.1",
                            "ROS_DOMAIN_ID=0",
                    ],
                    "network_mode": "host",
                    "logging": {
                            "driver": "none"
                    }
                }
            }
        }
        return DockerComposeServiceInstance(
            docker_compose_src_on_pc="./tmp/ros2_dc.yml",
            docker_compose_dst_on_vpu="~/ros2_dc.yml",
            tag_to_pull_from_registry="ifm3d-ros:humble-arm64",
            docker_image_src_on_pc=self.docker_image_src_on_pc,
            docker_image_dst_on_vpu=self.docker_image_dst_on_vpu,
            docker_compose=ros2_docker_compose
        )

    def docker_build_step(self):
        dockerfile_path = (Path(
            self.deploy_context["docker_build_dir"]) / "ros2" / "ros2.Dockerfile").as_posix()
        docker_build(
            build_dir=self.deploy_context["docker_build_dir"],
            dockerfile_path=dockerfile_path,
            repo_name="ifm3d-ros:humble-arm64",
            docker_build_output_path=str(self.docker_image_src_on_pc),
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
            target="base_dependencies",
            registry_host=self.deploy_context["docker_registry_host_relative_to_pc"],
            registry_port=self.deploy_context["docker_registry_port"]
        )
        docker_build(
            build_dir=self.deploy_context["docker_build_dir"],
            dockerfile_path=dockerfile_path,
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
            registry_host=self.deploy_context["docker_registry_host_relative_to_pc"],
            registry_port=self.deploy_context["docker_registry_port"],
        )

    def predeployment_setup(self, *args, **kwargs):
        pass


demo_deployment_components["ros2"] = Ros2DemoDeploymentComponents

# ## to enable desktop gui applications:
# # on nt:
# docker run -it -v /tmp/.X11-unix:/tmp/.X11-unix --env=QT_X11_NO_MITSHM=1 --net=host ifm3d-ros:humble-amd64
# # on ubuntu:
# docker run -d -v /tmp/.X11-unix:/tmp/.X11-unix --env=QT_X11_NO_MITSHM=1 --env=DISPLAY=:0 --net=host --name=humble ifm3d-ros:humble-amd64

# docker exec -it ros2 bash -c '. /opt/ros/humble/setup.bash && rviz2'
