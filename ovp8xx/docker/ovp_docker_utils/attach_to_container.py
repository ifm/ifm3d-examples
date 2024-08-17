
# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import sys
from pathlib import Path
import os

import typer

sys.path.append(str(Path(__file__).parent.parent))
from ovp_docker_utils.ovp_handle import logger, OVPHandle, OVPHandleConfig

#%%
def attach(
    container_name: str = "",
    IP: str = "192.168.0.69",
    log_dir: str = "logs",
    seconds_of_output: int = 0,
    ssh_key_file_name: str = "id_rsa_ovp8xx",
    stop_upon_exit: bool = False,
    ):
    """
    Attach to a running container and get the output via stdout

    Args:
        container_name (str): Name of the container to attach to, e.g. "example_python" for the python logging example, Default is "", which will attach to the first running container if there is only one.
        IP (str, optional): IP address of the ovp. Defaults to "192.168.0.69"
        log_dir (str, optional): Directory to store the logs. Defaults to "logs"
        seconds_of_output (int, optional): Number of seconds to get the output from the container. Defaults to 0, which means pipe data until the container stops.

    """
    os.chdir(Path(__file__).parent)
    
    ovp = OVPHandle(
        OVPHandleConfig(
            IP=IP,
            log_dir = log_dir,
            ssh_key_file_name=ssh_key_file_name,
        )
    )

    running_containers = [ container_info["NAMES"] for container_info in ovp.get_running_docker_containers() if "Up" in container_info["STATUS"] ]
    
    if running_containers:
        if container_name:
            if container_name not in running_containers:
                logger.error(f"Container {container_name} is not running.")
                container_name = ""
        elif len(running_containers) == 1:
            container_name = running_containers[0]
        else:
            logger.error(f"Multiple containers are running: ({running_containers}). Please specify the container name.")
            return
    
    logger.info(f"Attaching to container: '{container_name}'")
    if container_name:
        output_from_container = ovp.attach_to_container(
            container_name=container_name,
            pipe_duration= seconds_of_output, # 0 means pipe until the container stops
            stop_upon_exit=stop_upon_exit,
        )
    else:
        logger.error("No container to attach to.")
        output_from_container = ""
    return output_from_container

if __name__ == '__main__':
    if "ipykernel" not in sys.modules:
        typer.run(attach)
    else:
        output_from_container = attach()
# %%
