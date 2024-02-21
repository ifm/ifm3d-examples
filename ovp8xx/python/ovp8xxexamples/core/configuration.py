#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import json
from ifm3dpy.device import O3R


def main(ip, port):
    # Initialize the O3R object
    o3r = O3R(ip=ip)

    # Get the current configuration
    config = o3r.get()

    # Print a little part from the config to verify the configuration
    print(
        f'Firmware version: {json.dumps(config["device"]["swVersion"]["firmware"], indent=4)}'
    )

    print(f'State of port {port}: {config["ports"][port]["state"]}')

    # Let's change the name of the device
    o3r.set({"device": {"info": {"name": "great_o3r"}}})

    # Double check the configuration
    config = o3r.get()
    print(f'Device name: {config["device"]["info"]["name"]}')


if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
        PORT = config.PORT_2D
    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        PORT = "port0"
    main(ip=IP, port=PORT)
