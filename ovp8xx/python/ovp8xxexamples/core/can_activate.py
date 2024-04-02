#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from ifm3dpy.device import O3R
import logging
import time


def vpu_reboot(o3r):
    logging.info('Initiating rebooting the Device')
    o3r.reboot()
    time.sleep(150)
    logging.info('Device should be available again')
    available_ports = o3r.get(["/ports"])["ports"]
    for p in available_ports:
        if o3r.get([f'/ports/{p}/state'])['ports'][p]['state']=="ERROR":
            return False
    if o3r.get([f'/device/status'])['device']['status']=="ERROR":
        return False
    return True

def main():
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
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Device IP: {IP}")
    o3r = O3R(IP)

    # Get the can0 information: active status and bitrate
    can_info = o3r.get(["/device/network/interfaces/can0"])["device"]["network"]["interfaces"]["can0"]

    if not can_info["active"]:
        logging.info("activating can0 interface")
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
        logging.info("activating can0 interface failed")
    else:
        logging.info("can0 interface is active!")

if __name__ == "__main__":
    main()