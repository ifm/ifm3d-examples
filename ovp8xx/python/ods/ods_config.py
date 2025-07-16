# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This script is configuring an ODS application with one camera plugged to the port2
# It is assumed that the camera is mounted horizontally with the label facing upward.
# The default camera height is 35 cm, but this can be modified in the config file.

import json
import pathlib

from ifm3dpy.device import O3R, Error
from ifm3dpy.framegrabber import FrameGrabber


def async_diagnostic_callback(message: str, app_instance: str) -> None:
    """
    Callback to handle diagnostic messages and monitor the status of a specific application.

    Args:
        message (str): Diagnostic message in JSON format.
        app_instance (str): Name of the application instance to monitor (e.g., "app0").
    """
    diagnostic = json.loads(message)
    groups = diagnostic.get("groups", {})
    app_status = groups.get(app_instance, "unknown")
    print(f"\nNew Diagnostic: The status of application '{app_instance}': {app_status}")
    if app_status == "critical":
        print(
            f"⚠️ Application '{app_instance}' is in a critical state! Stop the Robot!!"
        )


def main(ip, config_file):
    o3r = O3R(ip)

    # Reset any previously present app
    print("Resetting applications... This may take a while.")
    o3r.reset("/applications")

    # Load the configuration from file
    actual_path = pathlib.Path(__file__).parent.resolve()
    try:
        with open(actual_path / config_file, "r") as f:
            config_snippet = json.load(f)
            app_instance = next(iter(config_snippet["applications"]["instances"]))
    except OSError as err:
        print("Error while reading configuration file")
        raise err

    # Setting the configuration from config file
    try:
        o3r.set(config_snippet)
        print("Setting the configuration")
    except Error as err:
        print("Error while setting the configuration")
        raise err

    # Set the application to run state
    print("Setting the application to RUN state")
    o3r.set(
        {
            "applications": {
                "instances": {app_instance: {"class": "ods", "state": "RUN"}}
            }
        }
    )

    # Start diagnostic monitoring with a separate FrameGrabber
    diag_fg = FrameGrabber(o3r, 50009)
    diag_fg.on_async_error(
        callback=lambda id, message: async_diagnostic_callback(message, app_instance)
    )
    print("Starting async diagnostic monitoring...")
    diag_fg.start([])

    # Check if the application has been correctly applied
    expected_name = config_snippet["applications"]["instances"][app_instance]["name"]
    app_name = o3r.get([f"/applications/instances/{app_instance}/name"])
    actual_name = app_name["applications"]["instances"][app_instance]["name"]
    status = "✅ Match" if actual_name == expected_name else "❌ Mismatch"
    print(
        f"Checking application name: Expected '{expected_name}', Applied '{actual_name}' → {status}"
    )

    print("Basic ODS configuration completed!")


if __name__ == "__main__":
    ip = "192.168.0.69"
    config_file = "configs/ods_one_head_config.json"
    main(ip, config_file)
