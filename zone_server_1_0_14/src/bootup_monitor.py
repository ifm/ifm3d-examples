#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
import ifm3dpy

import time
import platform  # For getting the operating system name
import subprocess  # For executing a shell command
import logging

logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)
logging.getLogger().setLevel(logging.DEBUG)


def ping(host):
    """
    Returns True if host (str) responds to a ping request.
    Remember that a host may not respond to a ping (ICMP) request even if the host name is valid.
    """

    # Option for the number of packets as a function of
    param = "-n" if platform.system().lower() == "windows" else "-c"

    # Building the command. Ex: "ping -c 1 google.com"
    command = ["ping", param, "1", host]

    return subprocess.call(command) == 0


def monitor_bootup(o3r: ifm3dpy.O3R, address, timeout=25, wait_time=0.5):
    """
    Check that the VPU completes it's boot sequence before attempting to initialize an application.

    Args:
        o3r (ifm3dpy.O3R): O3R handle
        timeout (int, optional): Maximum time expected for bootup sequence in seconds. Defaults to 25.
        wait_time (int, optional): how long to pause between queries to the VPU. Defaults to .5.

    Raises:
        TimeoutError: If no valid response is recieved from VPU within the timeout duration, this raises.
    """

    logger.info("Monitoring bootup sequence...")
    status = "Ready to connect..."
    logger.info(status)

    start = time.perf_counter()
    config = None
    while time.perf_counter() - start < timeout:
        if False:  # not ping(address):
            new_status = "Awaiting successful ping from VPU..."
        else:
            try:
                config = o3r.get()
                new_status = "Connected..."
            except:
                new_status = "Awaiting data from VPU..."

            if config:
                if "applications" in config["device"]["diagnostic"]["confInitStages"]:
                    new_status = "Ready to setup applications"
                    # logger.info("Ready to setup applications.")
                    break
                elif "ports" in config["device"]["diagnostic"]["confInitStages"]:
                    new_status = "Ports have been recognized..."
                elif "device" in config["device"]["diagnostic"]["confInitStages"]:
                    new_status = "VPU initializing..."

            # from pprint import pprint
            # pprint(config)

        if new_status != status:
            logger.info(new_status)
            status = new_status

        time.sleep(wait_time)
    else:
        raise TimeoutError("Process timed out waiting for VPU to boot")


if __name__ == "__main__":
    ADDR = "192.168.0.69"
    o3r = ifm3dpy.O3R(ADDR)
    monitor_bootup(o3r)

# %%
