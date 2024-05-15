#!/usr/bin/env python3
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# The CAN interface can only be activated with firmware
# versions 1.4.X or higher
from ifm3dpy.device import O3R
import logging
import time

logger = logging.getLogger(__name__)

def _check_can_availability(o3r)-> None:
    if "can0" in o3r.get(["/device/network/interfaces"])["device"]["network"]["interfaces"]:
        # Get the can0 information: active status and bitrate
        can_info = o3r.get(["/device/network/interfaces/can0"])["device"]["network"]["interfaces"]["can0"]
        return can_info
    else:
        raise RuntimeError("CAN interface not available in current firmware version.")
        
        

def main(ip: str) -> None:
    o3r = O3R(ip)
    can_info = _check_can_availability(o3r)
    if not can_info["active"]:
        logger.info("activating can0 interface ...")
        o3r.set({
            "device": {
                "network": {
                    "interfaces": {
                        "can0": {
                            "active": True
                            #"bitrate": '125K' # here set the bitrate '250K', '500K' ...

                        }
                    }
                }
            }
        })
        logger.info("Rebooting the device...")
        o3r.reboot()
        time.sleep(150)
        # For the sake of simplicity we assume that the boot-up process is not timing out,
        # and we simply check that the boot sequence has completed.
        # For a fool proof boot-up monitoring, review the bootup_monitor.py example.
        if not o3r.get(["/device/diagnostic/confInitStages"])["device"]["diagnostic"]["confInitStages"] == ["device", "ports", "applications"]:
            raise Exception("VPU not properly booted")

    can_info = o3r.get(["/device/network/interfaces/can0"])["device"]["network"]["interfaces"]["can0"]
    if not can_info["active"]:
        raise RuntimeError("Activating the can0 interface failed.")
    else:
        logger.info("The can0 interface is active!")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
    except ImportError:
        # Otherwise, use default values
        logger.warning(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        logger.warning("Defaulting to the default configuration.")
        IP = "192.168.0.69"
    
    logger.info(f"Device IP: {IP}")
    main(IP)