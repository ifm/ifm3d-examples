# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################


# %%#########################################
# This script is meant to be run interactively or as a script to demonstrate the deployment of services by reusing or extending existing deployment components.
# The deployment example script can also be run interactively like this so that you can observe each step closely.
#############################################

import os
from pprint import pprint

from deployment_examples import deploy
from deployment_components import demo_deployment_components
from attach_to_container import attach

from ovp_docker_utils import Manager, ManagerConfig

if __name__ == "__main__":
    ...
    #%% #############################################
    # setup ad-hoc network parameters
    #################################################
    
    IP = os.environ.get("IFM3D_IP", "192.168.0.69")
    gateway = ""
    print(f"Using IP: {IP}")

    #%% #############################################
    # observe the available demo services
    ################################################

    print("Available demo services:")
    pprint(list(demo_deployment_components.keys()))

    #%% #############################################
    # initialize a manager object, this is the interface used by deploy() and attach() to interact with the device, but you can use it directly as well.
    ################################################

    manager = Manager(ManagerConfig(
        IP = IP,
        possible_initial_ip_addresses_to_try=["192.168.0.60"],
        gateway = gateway,
        ssh_key_file_name = "id_rsa_ovp8xx", # this is the name specified for connection to the device when using deploy(), when connecting, it is appended to the authorized key list on the device.
    ))

    manager.mount_usb()

    print(f"fw_version: {manager.fw_version}")
    
    ssh_client = manager.ssh

    stdin, stdout, stderr = ssh_client.exec_command(
        "echo 'Hello, world! (echoed back from the device)'")
    print(stdout.read().decode())

    #%% #############################################
    # Wrap the deploy() function for accellerated integration testing, see the docstring for more details.
    ################################################

    output_from_container = deploy(
        ip=IP,
        gateway=gateway,
        docker_rebuild=False, # toggle this to false if the docker image is already built, this saves a few seconds of waiting for docker to check for cached layers, etc.
        tar_image_transfer=False, # toggle this to False to use use the registry rather than a tar file transfer (much faster)
        service_name = "python_logging", # try looping over the available demos to see which work on your device and which do not (do this with tar_image_transfer=False and purge_docker_images_on_VPU=True to accellerate the process and avoid running out of disk space on the device)
        additional_deployment_components=demo_deployment_components, # add more components here, modified from the demo components.
        disable_autostart=True, # each call will remove remove all services set to autostart, so this is a good idea to leave as True if you are testing multiple services.
        enable_autostart=True, # This will register this docker-compose service to start on boot.
        seconds_of_output=20, # how long to wait for output from the container before returning

    )

    # %%
    output_from_container = attach(
        IP = IP,
        seconds_of_output=25,
        stop_upon_exit = True, # will stop the container once the attach once the time is up or the keyboard interrupt(Ctrl-C) is received.
    )
    # %%
