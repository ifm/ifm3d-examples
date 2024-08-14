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

from ovp_docker_utils.deploy import deploy, logger
from ovp_docker_utils.deployment_components import demo_deployment_components
from attach_to_container import attach

from ovp_docker_utils import OVPHandle, OVPHandleConfig

if __name__ == "__main__":
    ...
    #%% #############################################
    # setup ad-hoc network parameters
    #################################################
    
    IP = os.environ.get("IFM3D_IP", "192.168.0.69")
    gateway = "192.168.0.15"
    print(f"Using IP: {IP}")

    # #%% #############################################
    # # observe the available demo services
    # ################################################

    # print("Available demo services:")
    # pprint(list(demo_deployment_components.keys()))

    # #%% #############################################
    # # initialize a device object, this is the interface used by deploy() and attach() to interact with the device, but you can use it directly as well.
    # ################################################

    device = OVPHandle(OVPHandleConfig(
        IP = IP,
        possible_initial_ip_addresses_to_try=["192.168.0.60"],
        gateway = gateway,
        ssh_key_file_name = "id_rsa_ovp8xx", # this is the name specified for connection to the device when using deploy(), when connecting, it is appended to the authorized key list on the device.
    ))

    device.mount_usb()

    logger.info(f"fw_version: {device.fw_version}")

    logger.info(
        device.o3r.get()["device"]["swVersion"]
    )
    
    ssh_client = device.ssh

    stdin, stdout, stderr = ssh_client.exec_command(
        "echo 'Test SSH command! (echoed back from the device)'")
    logger.info(stdout.read().decode())

    #%% #############################################
    # Wrap the deploy() function for accellerated integration testing, see the docstring for more details.
    ################################################

    output_from_container = deploy(
        ip=IP,
        gateway=gateway,
        docker_rebuild=True, # toggle this to false if the docker image is already built, this saves a few seconds of waiting for docker to check for cached layers, etc.
        tar_image_transfer=False, # toggle this to False to use use the registry rather than a tar file transfer (much faster, once transfered, or if small changes are made to the image)
        replace_existing_image=False, # if set to false, the image will not be replaced if it is already on the device, which is useful if you are using tar image transfer but don't want to wait for the image to be transferred again.
        service_name = "ifm3dlab", # try looping over the available demos to see which work on your ovp and which do not (do this with tar_image_transfer=False and purge_docker_images_on_OVP=True to accellerate the process and avoid running out of disk space on the device)

        # reset_vpu=True, # this will reset the OVP before deploying the service, this is useful if the device is in a bad state and you want to start fresh.
        purge_docker_images_on_OVP=False, # this will remove all docker images on the device before deploying the new one, this is useful for testing multiple services on a device with limited disk space.
        
        additional_deployment_components=demo_deployment_components, # add more components here, either extending or modifying the demo components.
        disable_autostart=True, # each call will remove remove all services set to autostart, so this is a good idea to leave as True if you are testing multiple services.
        enable_autostart=True, # This will register this docker-compose service to start on boot.
        seconds_of_output=100000, # how long to wait for output from the container before returning
        time_server = "time.google.com", # set the time server for the device (only works if the device is connected to the internet)
    )

    # # # %%
    # output_from_container = attach(
    #     IP = IP,
    #     seconds_of_output=20,
    #     stop_upon_exit = False, # will stop the container once the attach once the time is up or the keyboard interrupt(Ctrl-C) is received.
    # )
    # %%