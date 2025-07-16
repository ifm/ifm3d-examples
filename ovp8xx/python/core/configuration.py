# -*- coding: utf-8 -*-
#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import json

from ifm3dpy.device import O3R


def main(ip, port):
    # Initialize the O3R object
    o3r = O3R(ip=ip)

    # Retrieve and display the full configuration
    config = o3r.get()
    print("Full Configuration Retrieved:")
    print(json.dumps(config, indent=4))

    # Display firmware version
    firmware_version = config["device"]["swVersion"]["firmware"]
    print(f"Firmware version: {firmware_version}")

    # Check and display the state of the specified port
    if port in config["ports"]:
        port_state = config["ports"][port]["state"]
        print(f"State of port {port}: {port_state}")
    else:
        print(f"Port {port} does not exist in the configuration.")

    # Demonstrate retrieving specific configuration snippets
    print("\nExample: Retrieving specific configuration snippets...")
    snippets_to_retrieve = [
        [],  # Full configuration
        ["/device/swVersion/firmware"],  # Firmware version
        ["/device/status", "/ports/port0/info"],  # Multiple paths
    ]
    for paths in snippets_to_retrieve:
        snippet = o3r.get(paths)
        print(f"Configuration for {paths}: {json.dumps(snippet, indent=4)}")

    # Change the device name
    new_device_name = "great_o3r"
    o3r.set({"device": {"info": {"name": new_device_name}}})
    applied_name = o3r.get(["/device/info/name"])["device"]["info"]["name"]
    if applied_name != new_device_name:
        print(f"Failed to change device name to: {new_device_name}")
    else:
        print(f"Device name changed to: {applied_name}")

    # Demonstrate setting a valid multi path configuration snippet
    valid_snippet = {
        "device": {"info": {"description": "O3R device for demonstration"}},
        "ports": {port: {"info": {"name": "demo_port"}}},
    }
    try:
        o3r.set(valid_snippet)
        print("Configuration successfully updated.")
    except Exception as e:
        print(f"Failed to set configuration: {e}")


if __name__ == "__main__":
    IP = "192.168.0.69"
    PORT = "port0"
    main(ip=IP, port=PORT)
