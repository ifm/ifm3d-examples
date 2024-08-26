# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %% [markdown] - ovp_docker_utils intro ############################
"""
# OVP8xx Docker Utilities

Development in docker solves a number of important problems of reproducibility and isolation, but it also introduces a number of new challenges, such as how to deploy services to the device, how to interact with the device, how to debug the services, etc.
<br><br>

The purpose of this ovp_docker_utils package is to provide a set of tools to make it easier to deploy services to the device, interact with the device, and debug the services.
<br><br>

This script is meant as a primer on the basic primitives of the package, and how to use them to deploy a service to the device. It will build up a service from scratch, deploy it to the device, and then attach to the service to observe the output.
<br><br>

These tools are not provided as a production-ready solution, but rather as a starting point for developing your own tools and workflows for deploying services to the device.
<br><br>

Even if we produced kubernetes or ansible examples, we would still need a cohesive toolkit to extend those tools for the specific needs of developing on this platform. Additionally, an end user (eg. robot technician) should have very minimal requirements for deployment.
<br><br>

With a prebaked .tar docker image, one should be able to deploy an application with just a python environment on either Windows or Ubuntu.
"""
import os
from pprint import pprint

# hardcode the IP address of the device, this can be overridden by setting the IFM3D_IP environment variable.
IP = os.environ.get("IFM3D_IP", "192.168.0.69")

# %% [markdown] - ssh key generation ################################
"""
## ssh_key_gen.py

This script is used to generate a new ssh key pair for the device. The public key is then appended to the authorized_keys file on the device, and the private key is saved to the local machine. This key pair is used to connect to the device via ssh and scp.
"""

from ovp_docker_utils.ssh_key_gen import assign_key, DEFAULT_KEY_SIZE, DEFAULT_KEY_TITLE, SSH_DIR, test_key

private_key_path = assign_key(
    ip=IP,
    key_title=DEFAULT_KEY_TITLE,
    key_size=DEFAULT_KEY_SIZE,
    target_dir=SSH_DIR,
    owner="User exploring the OVP8xx docker utilities"
)

import paramiko
from ifm3dpy.device import  O3R

print(f"Key generated and assigned to device at {IP}")
print(f"testing SSH connection with key...")

o3r = O3R(IP)
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(o3r.ip, username="oem", key_filename=str(private_key_path))

stdin, stdout, stderr = ssh.exec_command(
    "echo 'Hello, world! (echoed back from the device)'")

print(stdout.read().decode())


# %% [markdown] - ssh_utilities #####################################
"""
## ssh_file_utils.py

This script is used to create an ssh connection to the device, and to perform basic file operations on the device, such as listing the contents of a directory, checking if a path exists, and transferring files to and from the device.
"""

from ovp_docker_utils.ssh_file_utils import SSH_collect_OVP_handles, SSH_path_exists, SSH_listdir, SCP_transfer_item, SSH_isdir, SSH_makedirs, SCP_synctree

ssh, scp = SSH_collect_OVP_handles(
    IP=IP,
    private_key_path=private_key_path,
    remove_known_host=True
)
print("Testing SSH connection to the device...\n")


tmp_dir = "/home/oem/tmp"
print(f"checking if a temp directory exists at '{tmp_dir}' on the device...")
print("found= "+str(SSH_path_exists(ssh, tmp_dir))+"\n")

print("Making a temp directory on the device...")
SSH_makedirs(ssh, tmp_dir)
print()

print("Adding a file to the temp directory...")
cmd = f"echo 'Hello, world!' > {tmp_dir}/hello.txt"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode(), stderr.read().decode())

print("Listing the contents of the temp directory:")
print(SSH_listdir(ssh, "/home/oem/tmp"))

print("Printing the contents of the file:")
cmd = f"cat {tmp_dir}/hello.txt"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode(), stderr.read().decode())

print("removing the temp directory...")
cmd = f"rm -rf {tmp_dir}"
stdin, stdout, stderr = ssh.exec_command(cmd)
print(stdout.read().decode(), stderr.read().decode())



# %% [markdown] - docker cli ########################################
"""
## docker_cli.py

This is a thin wrapper around the docker CLI, it is used to interact with the docker daemon on the device. It is used to build, push, and pull docker images. The goal here is to include any building and mirroring steps in the deployment process.
<br><br>

Docker remains a development requirement, but a technician who wants to deploy a service should not need to know how to build a docker image, nor have a registry running on their local machine to deploy a service. The deploy() function shown later in this script includes options to pull a remotely hosted .tar file or use a local .tar file to deploy a service without docker installed.
<br><br>

## Building a docker image
If docker is available, the docker_cli module will be used to wrap the docker CLI commands.

Two main build methods are available:
- build: builds a docker image from a Dockerfile
- dustynv_build: builds a docker image using the dusty_nv jetson-containers repo and involves using a modular package structure to build the image.

the get_dusty_nv_repo_if_not_found() function will prompt for a confirmation to clone the dusty_nv jetson-containers repo if it is not found in the ovp_docker_utils directory.
"""

from ovp_docker_utils.cli import cli_tee
from pathlib import Path
from ovp_docker_utils.docker_cli import build, save_docker_image, push_docker_image, prep_image_for_transfer, get_dusty_nv_repo_if_not_found, dustynv_build, docker_dir, tag_docker_image

docker_ps = "docker ps"
# print(f"Running command: {docker_ps}")
r, o, e = cli_tee("docker ps", show_i=True)
docker_available = ("CONTAINER ID" in o[0].decode())
if "nt" == os.name:
    r, o, e = cli_tee("docker ps", wsl=True, show_i=True)
    docker_available = docker_available and ("CONTAINER ID" in o[0].decode())
    if not docker_available:
        print("Docker is not available via WSL which means that arm64 images cannot be built on this system. The demo will continue, but the docker_cli module will not be used.")
elif not docker_available:
    print("Docker is not available on this system, the demo will continue, but the docker_cli module will not be used.")
if docker_available:
    print("Docker is available on this system, the docker_cli module may be used.")

if docker_available:

    parent_dir = Path(__file__).parent
    build_dir = parent_dir/"packages"/"ifm3d"
    tmp_dir = parent_dir/ "tmp"
    dockerfile_path = build_dir/"aggregated.Dockerfile"
    docker_build_output_path = (parent_dir/"ifm3dlab_test_deps.tar").as_posix()

    repo_name = "ifm3dlab"
    tag = repo_name+":arm64"

    output = build(
        build_dir=build_dir,
        dockerfile_path=dockerfile_path.as_posix(),
        tag=tag,
        build_args={
                "BASE_IMAGE": "nvcr.io/nvidia/l4t-base:r32.7.1",
            },
    )

    ifm3d_package_dirs = (docker_dir/"packages"/"*").as_posix()
    if get_dusty_nv_repo_if_not_found():
        print("dusty_nv repo available")
        ret, output, tag_generated = dustynv_build(
            packages = ["docker", "jupyterlab", "ifm3d"],
            additional_package_dirs=ifm3d_package_dirs,
            repo_name=repo_name,
            L4T_VERSION="32.7.4",
            CUDA_VERSION="10.2",
            PYTHON_VERSION="3.8",
            LSB_RELEASE="18.04",
        )
        tag_docker_image(tag_generated, tag)


# %% [markdown] - deployment overview ###############################
"""
### deployment strategies

There are several different options for deploying images to the VPU for development and production. to begin with, we can enumerate 4 main ways of getting an image onto the device:
<br><br>

1. Copy a .tar file to the device and load it into docker
<br><br>
2. Host a registry on the developer PC, and pull images to the VPU via ssh commands.
<br><br>
3. Pull directly from a remote repository such as dockerhub, nvcr.io, etc. to build the image on the device.
<br><br>
4. Download the image to the device as a .tar file and load it into docker.
<br><br>

Options 3 and 4 are not yet implemnented by any of the functions in this package, but they are possible with the current tools available in the package. This is because most vehicles do not provide gateway access to the VPU.
<br><br>

There are then 4 main ways of provisioning the image on the deployment pc so that it can be transferred to the VPU:
<br><br>

1. Build the image from a Dockerfile on the deployment pc
<br><br>
2. Build a docker image using the dusty_nv jetson-containers repo on the deployment pc
<br><br>
3. Download the image from a remote repository such as dockerhub, nvcr.io, etc.
<br><br>
4. Download the image to the deployment pc as a .tar file
<br><br>

So there are 4x4 main routes to deploy a dockerized service to the VPU.
<br><br>

Some of these strategies are more appropriate for development and testing, while others are more appropriate for production.
<br><br>

To better illustrate these options, the following diagram describes all of the options described above.
<br><br>

![Docker image deployment options](images/schematic.svg)
<br><br>

"""


# %% [markdown] - registry push #####################################
"""
### Use registry to store docker images so that they can be pulled by the device.

Start a local docker registry
<br><br>

```docker run -d -p 5005:5000 --name registry registry:latest```
<br><br>

On windows, you may need to open the port in the firewall for incoming tcp connections
"""
from ovp_docker_utils.docker_cli import push_docker_image

if docker_available:
    
    deployment_example_dir = Path(__file__).parent
    docker_registry_host_relative_to_pc = "localhost"
    docker_registry_port = 5005

    push_docker_image(
        tag = tag,
        registry_host=docker_registry_host_relative_to_pc,
        registry_port=docker_registry_port,
    )

# %% [markdown] - tar save ##########################################
"""
### Save the docker image to a .tar file
"""

from ovp_docker_utils.docker_cli import save_docker_image
if docker_available:
    save_docker_image(
        tag=tag,
        docker_build_output_path="ifm3dlab_test_deps.tar",
    )


# %% [markdown] - ovp_handle ########################################
"""
## ovp_handle.py

A guiding principle of the ifm3d library has been to limit magic as much as possible.
<br><br>

The ovp handle module provide convenience functions. that are used to interact with the device beyond the ifm3d api. It wraps the ssh utilities, as well as ifm3dpy, and the docker CLI on the device.
<br><br>

OVPhandle was chosen as it refers to the device as a whole, and not just the "o3r" camera heads referred to in the ifm3d library. As the Customer Support for Robotics team has put more mileage on these tools, we've moved more standard functionality from the deployment scripts to the OVPhandle class.
"""

from ovp_docker_utils.ovp_handle import OVPHandle, OVPHandleConfig, logger
from paramiko import SSHClient
from ifm3dpy import O3R

import logging

gateway = "192.168.0.15"

print(f"Using IP: {IP}")
ovp = OVPHandle(OVPHandleConfig(
    IP = IP,
    possible_initial_ip_addresses_to_try=["192.168.0.60"],
    gateway = gateway,
    ssh_key_file_name = "id_rsa_ovp8xx",
))

ovp.mount_usb()

logger.info(f"fw_version: {ovp.fw_version}")

o3r: O3R = ovp.o3r
ssh_client: SSHClient = ovp.ssh

logger.info(
    ovp.o3r.get()["device"]["swVersion"]
)

stdin, stdout, stderr = ssh_client.exec_command(
    "echo 'Test SSH command! (echoed back from the device)'")
logger.info(stdout.read().decode())


try:
    # These functions depend on the vpu being connected to the internet to sync time or pull the image from the internet.
    ovp.add_timeserver("time.google.com")
    # the time must be syncronised before a docker image can be pulled from dockerhub
    # In this case, a minimal container ~200MB is pulled from dockerhub to run chown -R in the /home/oem directory which ensures that any files copied to the device are owned by the oem user. This also eliminates any issues with permissions when copying files to the device. This will only be necessary if the user does not run docker containers with the same user/group ids as the oem user on the device.
    ovp.fix_file_permissions("python:slim-buster")
except Exception as e:
    logger.error(f"Error attempting to fix permissions: {e}")
    logger.info("Continuing with deployment...")
    
# %% [markdown] - deploy ############################################
"""
...
"""
...
# %% [markdown] - monitor ###########################################
"""
...
"""
...
# %% [markdown] - deployment components #############################
"""
...
"""
...
# %% [markdown] - common deployment components ######################
"""
...
"""
...
# %% [markdown] - ifm3dlab ##############################
"""
...
"""
...