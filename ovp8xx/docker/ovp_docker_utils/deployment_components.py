# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# This file contains the deployment components for the various demo services that can be deployed on the OVP

import os
import time
from pathlib import Path

from scp import SCPException

from .docker_build import docker_build, get_dusty_nv_repo_if_not_found, dustynv_build, prep_image_for_transfer, convert_nt_to_wsl
from .cli import cli_tee

from . import OVPHandle, logger, DockerComposeServiceInstance
from .ssh_file_utils import SCP_transfer_item

# %%#########################################
# Define typical structure of the docker-compose files which are used to define how the OVP runs the docker containers
#############################################


suggested_docker_compose_parameters = {
    "version": "2.4",
}
suggested_docker_compose_service_parameters = {
    "restart": "unless-stopped",
    "environment": [
        "ON_OVP=1",
        "IFM3D_IP=172.17.0.1"
    ],

    # The following line is used to pin the container to specific cores. This is useful if you want to ensure that the container does not interfere with the real-time performance of other applications running on the OVP (eg. the Obstacle Detection System)
    "cpuset": "0,3,4,5",

    # Rather than deploying configs or python applications by packaging them up in a container, you may prefer to deploy them using a directory shared between the host and the container
    "volumes": [
        "/home/oem/share/:/home/oem/share/",
    ],

    # # As of firmware 1.5.X the ordinary docker logger routes logs to the journalctl, a volatile record. previous releases would use persistant logging which could result in hammering of the ssd unless the logs were rotated or the docker logging driver was set to none.

    # "logging": {
    #     "driver": "none",
    # }
}


# %%#########################################
# Define the deployment components for the various services
#############################################

class DeploymentComponents:
    """A simple abstract class for deployment components. This class is meant to be subclassed and not used directly."""
    def __init__(self, **deploy_context):
        self.deploy_context = deploy_context

    def docker_compose_service_instance() -> DockerComposeServiceInstance:
        raise NotImplementedError

    def docker_build_step(self) -> None:
        raise NotImplementedError

    def predeployment_setup(self) -> None:
        pass # additional steps may not be necessary for all services


demo_deployment_components = {}

DEPLOYMENT_VERSION = "0.0.0" # optionally use to differentiate between different saved docker images
class IFM3DLabDeploymentComponents(DeploymentComponents):
    def __init__(
        self,
        packages: list = ["docker", "jupyterlab", "ovp_recorder"],
        mirroring_examples: bool = 1,
        **deploy_context
    ):
        # python and ifm3d is necessary for these deployment components
        if not packages:
            packages = ["python", "ifm3d"]
        elif "ifm3dpy" not in packages:
            packages.append("ifm3d")
        self.packages = packages

        self.mirroring_examples = mirroring_examples

        self.deploy_context = deploy_context
        self.name = "ifm3dlab"
        self.repo_name = "l4t-"+self.name
        self.tag = self.repo_name+f":{DEPLOYMENT_VERSION}-arm64"
        self.vpu_shared_volume_dir = "/home/oem/share"

        # determine the location of the docker image on the PC and OVP
        if self.deploy_context["tar_image_transfer"]:
            tar_image_file_name = f"{self.name}_{DEPLOYMENT_VERSION}-arm64.tar"
            self.docker_image_src_on_pc = self.deploy_context["tmp_dir"] + \
                f"/{tar_image_file_name}"
            self.docker_image_dst_on_vpu = f"~/{tar_image_file_name}"
        else:
            self.docker_image_src_on_pc = ""
            self.docker_image_dst_on_vpu = ""

    def docker_compose_service_instance(self) -> DockerComposeServiceInstance:
        docker_compose = {
            **suggested_docker_compose_parameters,
            "services": {
                self.name: {
                    "image": self.tag,
                    "container_name": self.name,
                    "network_mode": "host",
                    "runtime": "nvidia",
                    "working_dir": f"/home/oem/share",  
                    "entrypoint": "/bin/bash -c",               
                    **suggested_docker_compose_service_parameters
                }
            },
        }
        # add features specific to dusty-nv packages added to the docker image
        command = 'sleep infinity'
        if "ovp_recorder" in self.packages:
            command = f'python3 {self.vpu_shared_volume_dir}/ifm3d-examples/ovp8xx/docker/packages/ovp_recorder/ifm_o3r_algodebug/http_api.py && ' + command
        elif "ifm3d" in self.packages:
            command = f'python3 {self.vpu_shared_volume_dir}/ifm3d-examples/ovp8xx/docker/packages/ifm3d/python_logging.py'
        if "jupyterlab" in self.packages:
            # customize the service to your needs
            docker_compose["services"][self.name]["environment"]+=[
                "JUPYTER_PORT=8888",
                "JUPYTER_PASSWORD=ifm3dlab",
                "JUPYTER_ROOT=/",
                "JUPYTER_LOGS=/home/oem/share/jupyter.log",
            ]
            command = "/start_jupyter && " + command
        if "docker" in self.packages:
            # mount the docker socket so that you can run docker commands from within the container
            docker_compose["services"][self.name]["volumes"] += ["/var/run/docker.sock:/var/run/docker.sock"]

        docker_compose["services"][self.name]["command"] = f'"{command}"'

        docker_compose_fname = f"{self.name}_dc.yml"
        return DockerComposeServiceInstance(
            tag_to_run=self.tag,
            project_file_mapping=[
                # use self.predeployment_setup to transfer files to the OVP
            ],
            docker_image_src_on_pc=self.docker_image_src_on_pc,
            docker_image_dst_on_vpu=self.docker_image_dst_on_vpu,
            docker_compose_src_on_pc=self.deploy_context["tmp_dir"] + "/" + docker_compose_fname,
            docker_compose_dst_on_vpu="~/"+docker_compose_fname,
            docker_compose=docker_compose
        )

    def docker_build_step(self):

        # ## TODO use faster build step optionally rather than using the dustynv_build (fewer steps)
        # output = docker_build_and_save(
        #     build_dir=self.docker_build_dir,
        #     dockerfile_path=f"{self.docker_build_dir}/Dockerfile",
        #     tag=self.tag,
        #     docker_build_output_path=self.docker_image_src_on_pc,
        #     build_args={
        #         "BASE_IMAGE": "arm64v8/python:3.9.6-slim-buster",
        #         "ARCH": "arm64",
        #     },
        # )
        # output = push_to_registry(
        #     tag=self.tag,
        #     registry_host=self.deploy_context['docker_registry_host_relative_to_pc'],
        #     registry_port=self.deploy_context['docker_registry_port']
        # )


        get_dusty_nv_repo_if_not_found()
        ret, output, tag = dustynv_build(
            packages = self.packages,
            repo_name=self.repo_name,
            L4T_VERSION="32.7.4",
            CUDA_VERSION="10.2",
            PYTHON_VERSION="3.8",
            LSB_RELEASE="18.04",
        )
        print(f"pushing {tag} to registry with tag: {self.tag}")
        output = prep_image_for_transfer(
            docker_build_output_path= self.docker_image_src_on_pc,
            tag=self.tag,
            start_tag = tag,
            registry_host=self.deploy_context['docker_registry_host_relative_to_pc'],
            registry_port=self.deploy_context['docker_registry_port'],
        )

    def predeployment_setup(self):
        if not self.mirroring_examples:
            return
        
        from .ssh_file_utils import SCP_synctree
        from . import OVPHandle
        import re
        
        ovp: OVPHandle = self.deploy_context["ovp"]
        
        example_dir = Path(__file__).parent.parent.parent.parent.as_posix()
        example_dir_vpu = "/home/oem/share/ifm3d-examples"
        logger.info(f"Transferring examples to the OVP ({example_dir} -> {example_dir_vpu})...")
        
        relative_paths = [
            "/ovp8xx",
            # "/jetson-containers",
        ]
        exclude_patterns = [
            "/tmp/",
            "/.git/",
            "/logs/",
            "/__pycache__/",
            "/jetson-containers/",
            "venv"
        ] # middle of path
        exclude_file_extensions = [
            ".h5",
            "sh",
            ".tar",
            ".zip",
        ] # end of path

        # for path in relative_paths:
        #     absolute_path = example_dir + path
        #     for root, dirs, files in os.walk(absolute_path):
        #         relative_root = Path(root).as_posix().replace(example_dir, "")
        #         if not any(exclude_dir in relative_root+"/" for exclude_dir in exclude_patterns):
        #             # comment about transfers
        #             logger.info(f"Transferring contents of {relative_root}")
        #             for file in files:
        #                 if not any(file.endswith(ext) for ext in exclude_file_extensions):
        #                     try:
        #                         ovp.transfer_to_vpu(
        #                             src="/".join((example_dir,relative_root,file)),
        #                             dst="/".join((example_dir_vpu+relative_root,file)),
        #                             verbose = False
        #                         )
        #                     except SCPException as e:
        #                         logger.error(f"Transfer failed for {relative_root}/{file}: {e}")

        
        exclude_regex = '|'.join([
                        pattern for pattern in exclude_patterns]+[
                        f".*{ext}$" for ext in exclude_file_extensions])
        SCP_synctree(
            ssh=ovp.ssh,
            scp=ovp.scp,
            src=example_dir,
            dst=example_dir_vpu,
            src_is_local=True,
            exclude_regex=exclude_regex,
            verbose = True
        )


demo_deployment_components["ifm3dlab"] = IFM3DLabDeploymentComponents