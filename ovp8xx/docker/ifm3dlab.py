# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################


# %%#########################################
# This script is meant to be run interactively or as a script to demonstrate the deployment of services by reusing or extending existing deployment components.
# The deployment example script can also be run interactively like this so that you can observe each step closely.
#############################################

import os

import ovp_docker_utils.logs
from ovp_docker_utils.deploy import deploy, logger
from ovp_docker_utils.deployment_components import demo_deployment_components
from ovp_docker_utils.attach_to_container import attach
from ovp_docker_utils.ovp_handle import OVPHandle, OVPHandleConfig

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

    # #%+% #############################################
    # # initialize a device object, this is the interface used by deploy() and attach() to interact with the device, but you can use it directly as well.
    # ################################################

    ovp = OVPHandle(OVPHandleConfig(
        IP = IP,
        possible_initial_ip_addresses_to_try=["192.168.0.60"],
        gateway = gateway,
        ssh_key_file_name = "id_rsa_ovp8xx", # this is the name specified for connection to the device when using deploy(), when connecting, it is appended to the authorized key list on the device.
    ))

    ovp.mount_usb()

    logger.info(f"fw_version: {ovp.fw_version}")

    logger.info(
        ovp.o3r.get()["device"]["swVersion"]
    )
    
    ssh_client = ovp.ssh

    stdin, stdout, stderr = ssh_client.exec_command(
        "echo 'Test SSH command! (echoed back from the device)'")
    logger.info(stdout.read().decode())

    # %% #############################################
    # ovp.add_timeserver("time.google.com")
    # ovp.fix_file_permissions("python:slim-buster")
    # o3r=ovp.o3r
    # o3r.factory_reset(keep_network_settings=True)
    #%%

    #%% #############################################
    # Wrap the deploy() function for accellerated integration testing, see the docstring for more details.
    ################################################

    output_from_container = deploy(
        # reset_vpu=True, # this will reset the OVP before deploying the service, this is useful if the device is in a bad state and you want to start fresh.
        ip=IP,
        gateway=gateway,
        additional_deployment_components=demo_deployment_components,
        service_name = "ifm3dlab",
        # pc_image_aquisition_mode="remote-tar",
        pc_image_aquisition_mode="build-packages",
        dusty_nv_packages=",".join([
            "docker",
            "jupyterlab",
            "ovp_recorder",
            # "ifm_oem",
        ]),
        # image_delivery_mode="local-registry",
        image_delivery_mode="local-tar",
        docker_rebuild=1, # toggle this to false if the docker image is already built, this saves a few seconds of waiting for docker to check for cached layers, etc.
        purge_docker_images_on_OVP=1, # this will remove all docker images on the device before deploying the new one, this is useful for testing multiple services on a device with limited disk space.
        
        disable_autostart=True, # each call will remove remove all services set to autostart, so this is a good idea to leave as True if you are testing multiple services.
        enable_autostart=True, # This will register this docker-compose service to start on boot.
        seconds_of_output=10000, # how long to wait for output from the container before returning
        time_server = "time.google.com", # set the time server for the device (only works if the device is connected to the internet)
    )
    # %%
    attach(
        container_name="ifm3dlab",
        IP=IP,
        log_dir="logs",
        seconds_of_output=0,
        ssh_key_file_name="id_rsa_ovp8xx",
        stop_upon_exit=False,
    )
# %%
