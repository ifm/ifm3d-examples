#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from ifm3dpy.device import O3R
import logging
import time
import sys
from bootup_monitor import BootUpMonitor


def vpu_reboot(o3r):
    logging.info('Device rebooting after activation of can0 interface ...')
    o3r.reboot()
    time.sleep(150)
    # check if the reboot is successful
    bootup_monitor = BootUpMonitor(o3r)
    bootup_successfull = bootup_monitor.monitor_VPU_bootup()
    if bootup_successfull :
        logging.info('Device reboot successful')
    else :
        logging.error('Device reboot  not unsuccessful!!')
        

def check_version(version_string):
    major_str, minor_str, *_ = version_string.split('.')
    major = int(major_str)
    minor = int(minor_str)
    if (major == 1 and minor >= 4) or (major > 1 ):
        return True
    else:
        logging.error("Version is not 1.4.x or greater. Shutting down!")
        sys.exit(1)

def main(ip):
    o3r = O3R(ip)

    # Get the can0 information: active status and bitrate
    can_info = o3r.get(["/device/network/interfaces/can0"])["device"]["network"]["interfaces"]["can0"]
    fw_version = o3r.get(['/device/swVersion/firmware'])['device']['swVersion']['firmware']
    check_version(fw_version)
    if not can_info["active"]:
        logging.info("activating can0 interface ...")
        o3r.set({
            "device": {
                "network": {
                    "interfaces": {
                        "can0": {
                            "active": True
                        }
                    }
                }
            }
        })
        # the system needs a reboot after activating the can0 interface
        vpu_reboot(o3r)
    can_info = o3r.get(["/device/network/interfaces/can0"])["device"]["network"]["interfaces"]["can0"]
    if not can_info["active"]:
        logging.error("activating can0 interface failed")
    else:
        logging.info("can0 interface is active!")

if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
    # Configure logging
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    logging.info(f"Device IP: {IP}")

    main(IP)