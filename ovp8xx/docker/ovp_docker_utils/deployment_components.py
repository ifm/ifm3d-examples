# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# This file contains the deployment components for the various demo services that can be deployed on the OVP

from pathlib import Path

from ovp_docker_utils.docker_cli import build, get_dusty_nv_repo_if_not_found, dustynv_build, tag_docker_image, prep_image_for_transfer, convert_nt_to_wsl
from ovp_docker_utils.cli import cli_tee
from ovp_docker_utils.ovp_handle import OVPHandle, logger, DockerComposeServiceInstance
from ovp_docker_utils.docker_compose_instance import FileSystemMapping, RemoteTarSpec

STD_EXCLUDE_REGEX = "/tmp/|/.git/|/logs/|/__pycache__/|/jetson-containers/|venv|.*.h5$|.*sh$|.*.tar$|.*.zip$|.*.bz2$"

# %%#########################################
# Define typical structure of the docker-compose files which are used to define how the OVP runs the docker containers
#############################################

home = "/home/oem"
share = "/home/oem/share"

suggested_docker_compose_parameters = {
    "version": "2.4",
}
suggested_docker_compose_service_parameters = {
    "restart": "unless-stopped",
    "environment": [
        "ON_OVP=1",
        "IFM3D_IP=172.17.0.1",
    ],

    # The following line is used to pin the container to specific cores. This is useful if you want to ensure that the container does not interfere with the real-time performance of other applications running on the OVP (eg. the Obstacle Detection System)
    "cpuset": "0,3,4,5",

    # Rather than deploying configs or python applications by packaging them up in a container, you may prefer to deploy them using a directory shared between the host and the container
    "volumes": [
        f"{share}/:{share}/",
    ],

    # # As of firmware 1.5.X the ordinary docker logger routes logs to the journalctl, a volatile record. previous releases would use persistant logging which could result in hammering of the ssd unless the logs were rotated or the docker logging driver was set to none.

    # "logging": {
    #     "driver": "none",
    # }
}

# %%#########################################
# Define the deployment components for the various services
#############################################

from pydantic import BaseModel
class ImageSource(BaseModel):
    id: str = ""
    tag: str = ""
    tar_path: str = ""

class DeploymentComponents:
    """A simple abstract class for deployment components. This class is meant to be subclassed and not used directly."""
    def __init__(self, **deploy_context):
        self.deploy_context = deploy_context

    def docker_compose_service_instance(self) -> DockerComposeServiceInstance:
        raise NotImplementedError(f"This method is not implemented in {self.__class__.__name__}")

    def build(self) -> ImageSource:
        raise NotImplementedError(f"This method is not implemented in {self.__class__.__name__}")
    
    def build_packages(self) -> ImageSource:
        raise NotImplementedError(f"This method is not implemented in {self.__class__.__name__}")

    def predeployment_setup(self) -> None:
        pass # additional steps may not be necessary for all services



demo_deployment_components = {}

DEPLOYMENT_VERSION = "0.0.0" # optionally use to differentiate between different saved docker images


class IFM3DLabDeploymentComponents(DeploymentComponents):
    def __init__(
        self,
        packages: list = ["docker", "jupyterlab", "ovp_recorder"],
        **deploy_context
    ):

        self.deploy_context = deploy_context
        self.name = "ifm3dlab"
        self.repo_name = "l4t-"+self.name
        self.vpu_shared_volume_dir = share

        if self.deploy_context["pc_image_aquisition_mode"] in (
            "remote-tar",
            "build-packages"
            ):
            # python and ifm3d is necessary for dusty-nv packaging
            if not packages:
                packages = ["python", "ifm3d"]
            elif "ifm3dpy" not in packages:
                packages.append("ifm3d")
            self.packages = packages
            # self.docker_image_src_on_pc = f"{self.repo_name}.tar"

            self.tag = self.repo_name+f"-{'-'.join([p[:5] for p in packages])}:{DEPLOYMENT_VERSION}-arm64"
        else:
            self.packages = []
            # self.docker_image_src_on_pc = None
            self.tag = self.repo_name+f":{DEPLOYMENT_VERSION}-arm64"

    def docker_compose_service_instance(self) -> DockerComposeServiceInstance:
        docker_compose = {
            **suggested_docker_compose_parameters,
            "services": {
                self.name: {
                    "image": self.tag,
                    "container_name": self.name,
                    "network_mode": "host",
                    "runtime": "nvidia",
                    "working_dir": share,  
                    "entrypoint": "/bin/bash -c",               
                    **suggested_docker_compose_service_parameters
                }
            },
        }

        # add features specific to dusty-nv packages added to the docker image
        if "docker" in self.packages:
            # mount the docker socket so that you can run docker commands from within the container
            docker_compose["services"][self.name]["volumes"] += ["/var/run/docker.sock:/var/run/docker.sock"]
        if "jupyterlab" in self.packages:
            docker_compose["services"][self.name]["environment"]+=[
                "JUPYTER_PORT=8888",
                "JUPYTER_PASSWORD=ifm3dlab",
                "JUPYTER_ROOT=/",
                f"JUPYTER_LOGS={home}/share/jupyter.log",
            ]
        if "ifm_oem" in self.packages:
            oem_uid = self.deploy_context["oem_uid"]
            oem_gid = self.deploy_context["oem_gid"]
            user, group = "oem", "oem"
            docker_compose["services"][self.name]["user"] = f"{oem_uid}:{oem_gid}"
            docker_compose["services"][self.name]["environment"] += [        
                f"HOME={home}",
                f"USER={user}",
                f"GROUP={group}",
            ]

        command = "echo 'Container initialized!'"

        jupyter_pw = "ifm3dlab"
        if "jupyterlab" in self.packages and "ifm_oem" in self.packages:
            script = r"from jupyter_server.auth.security import set_password; set_password(\\\'ifm3dlab\\\', \\\'/home/oem/.jupyter/jupyter_server_config.json\\\')"
            command += f' && python3 -c \\\"exec(\'{script}\')\\\"'
        if "jupyterlab" in self.packages:
            command  += " && /start_jupyter"
        if "ovp_recorder" in self.packages:
            command += f' && python3 {self.vpu_shared_volume_dir}/ifm3d-examples/ovp8xx/docker/packages/ovp_recorder/ifm_o3r_algodebug/http_api.py'
        if "ifm3d" in self.packages:
            command += f' && python3 {self.vpu_shared_volume_dir}/ifm3d-examples/ovp8xx/docker/packages/ifm3d/python_logging.py'
        script = r"import time\nimport ifm3dpy\nfor x in range(int(1e10)):\n    print(f\\\'ifm3dpy=={ifm3dpy.__version__}\\\')\n    time.sleep(5)"
        command += f' && python3 -c \\\"exec(\'{script}\')\\\"'


        docker_compose["services"][self.name]["command"] = f'"{command}"'
        
        example_dir = Path(__file__).parent.parent.parent.parent.as_posix()
        example_dir_vpu = "/home/oem/share/ifm3d-examples"

        remote_tar_full = RemoteTarSpec(
            url = "https://www.dropbox.com/scl/fi/dyn5uwqte9x40l4jqlx7y/l4t-ifm3dlab-docke-jupyt-ovp_r-ifm3d.0.0.0-arm64.tar.bz2?rlkey=2zhzupajliqnrrqq9is66n82q&st=7nlkc0wg&dl=0".replace("www.dropbox.com", "dl.dropboxusercontent.com"),
            id = "833b50975ec4",
            fname = "l4t-ifm3dlab-docke-jupyt-ovp_r-ifm3d.0.0.0-arm64.tar.bz2",
            sha_256 = "ec9872d211ca7beab288340fd10afb492ff7e17988e230722eadc09ed92e7124"
        )
        remote_tar_base = RemoteTarSpec(
                url = "https://www.dropbox.com/scl/fi/b5wl1zvub01eebl4ro2ja/l4t-ifm3dlab.0.0.0-arm64.tar.bz2?rlkey=auzdlol02xrpnupcfp1fzzre9&st=pmdwe4ne&dl=0".replace("www.dropbox.com", "dl.dropboxusercontent.com"),
                fname = "l4t-ifm3dlab.0.0.0.arm64.tar.bz2",
                sha_256 = "c322e9d5e0b0841c58b15e879aee725f1180dd365434a0034afb0e602a62e69d"
            )

        instance = DockerComposeServiceInstance(
            # remote_tar = None, #default
            file_system_mappings = [
                FileSystemMapping(
                    src = example_dir + "/ovp8xx/",
                    dst = example_dir_vpu + "/ovp8xx",
                    exclude_regex = STD_EXCLUDE_REGEX
                )
            ],
            tmp_dir_on_vpu = "/home/oem/tmp", # default
            tag_to_run=self.tag,
            docker_compose=docker_compose,
            remote_tar= remote_tar_full
        )
        
        return instance

    def build(self):
        project_dir = (Path(__file__).parent.parent / "packages" / "ifm3d").as_posix()

        dockerfile = f"{project_dir}/aggregated.Dockerfile"

        # assert not any(package in ["docker", "jupyterlab", "ovp_recorder"] for package in self.packages), "The packages 'docker', 'jupyterlab', and 'ovp_recorder' are specified but cannot be successfully build using the minimal dockerfile {dockerfile}. Please use the build-packages image aquisition method to build the docker image with these packages."

        output = build(
            build_dir=project_dir,
            dockerfile_path=dockerfile,
            tag=self.tag,
            build_args={
                "BASE_IMAGE": "nvcr.io/nvidia/l4t-base:r32.7.1",
                "ARCH": "arm64",
            },
            # Additional_build_params="--no-cache"
        )
        return ImageSource(tag=self.tag)

    def build_packages(self):
             
        # TODO, use the ovp handle to check the version of the firmware and select the appropriate dusty-nv build parameters

        docker_dir = Path(__file__).parent.parent
        ifm3d_package_dirs = (docker_dir/"packages"/"*").as_posix()

        get_dusty_nv_repo_if_not_found()
        ret, output, tag = dustynv_build(
            packages = self.packages,
            repo_name=self.repo_name,
            L4T_VERSION="32.7.4",
            CUDA_VERSION="10.2",
            PYTHON_VERSION="3.8",
            LSB_RELEASE="18.04",
            additional_package_dirs=ifm3d_package_dirs,
        )
        tag_docker_image(tag, self.tag)
        return ImageSource(tag=self.tag)

        

    def predeployment_setup(self):
        
        ...
        # from .ssh_file_utils import SCP_synctree
        # from . import OVPHandle
        # import re
        
        # ovp: OVPHandle = self.deploy_context["ovp"]
        
        # example_dir = Path(__file__).parent.parent.parent.parent.as_posix()
        # example_dir_vpu = "/home/oem/share/ifm3d-examples"
        # logger.info(f"Transferring examples to the OVP ({example_dir} -> {example_dir_vpu})...")
        
        # SCP_synctree(
        #     ssh=ovp.ssh,
        #     scp=ovp.scp,
        #     src=example_dir,
        #     dst=example_dir_vpu,
        #     src_is_local=True,
        #     exclude_regex=STD_EXCLUDE_REGEX,
        #     verbose = True
        # )

demo_deployment_components["ifm3dlab"] = IFM3DLabDeploymentComponents