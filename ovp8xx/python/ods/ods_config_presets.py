# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This script is configuring an ODS application with 2 cameras plugged to the port2 and port3
# It is assumed that the camera is positioned horizontally with the label facing upward.
# The default camera heights are 35 cm, but these can be modified in the config file.
#
#          [CAM]       <-- Front Camera (port2) horizontally with the label facing upward.
#            |
#      |-----------|   <-- Robot body
#      |   Robot   |
#      |-----------|
#            |
#          [CAM]       <-- Back Camera (port3) horizontally with the label facing upward.
#
#  This script is designed to simulate the use case of a robot equipped with two cameras:
#  one at the front and one at the back.

import json
import pathlib
import time

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


def change_preset(o3r: O3R, app_instance: str, preset_idx: int) -> None:
    """
    Change the preset of the specified application and verify the change.

    Args:
        o3r (O3R): The O3R device object.
        app_instance (str): The application port (e.g., "app0").
        preset_idx (int): The identifier of the preset to load.
    """
    print(f"Loading preset with identifier {preset_idx}")
    o3r.set(
        {
            "applications": {
                "instances": {
                    app_instance: {
                        "presets": {
                            "load": {"identifier": preset_idx},
                            "command": "load",
                        }
                    }
                }
            }
        }
    )
    loaded_preset = o3r.get(
        [
            "/applications/instances/"
            + app_instance
            + "/configuration/zones/zoneConfigID"
        ]
    )["applications"]["instances"][app_instance]["configuration"]["zones"][
        "zoneConfigID"
    ]
    if loaded_preset == preset_idx:
        print(f"Preset with identifier {loaded_preset} loaded successfully")
    else:
        print(
            f"Preset with identifier {preset_idx} has been set but actual preset identifier is {loaded_preset}"
        )


def main(ip, config_file):
    o3r = O3R(ip)

    # Reset any previously present app
    print("Resetting applications")
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

    # setting the configuration from config file
    try:
        print("Setting the loaded configuration")
        o3r.set(config_snippet)
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

    # Load a predefined preset using its identifier
    change_preset(o3r, app_instance, preset_idx=1)
    time.sleep(5)

    # Loading another preset
    change_preset(o3r, app_instance, preset_idx=2)
    time.sleep(5)

    # Attempt to change configuration while in RUN state (expected to fail)
    try:
        print("Trying to change a conf parameter while the app is in RUN state.")
        print("This is expected to fail!")
        o3r.set(
            {
                "applications": {
                    "instances": {
                        app_instance: {
                            "configuration": {"grid": {"rangeOfInterest": 10.0}}
                        }
                    }
                }
            }
        )
    except Exception:
        print("Cannot set a CONF parameter while app is in RUN state")

    try:
        print("Trying to change a CONF parameter while the app is in CONF state")
        o3r.set(
            {
                "applications": {
                    "instances": {app_instance: {"class": "ods", "state": "CONF"}}
                }
            }
        )
        o3r.set(
            {
                "applications": {
                    "instances": {
                        app_instance: {
                            "configuration": {"grid": {"rangeOfInterest": 10.0}}
                        }
                    }
                }
            }
        )
        o3r.set(
            {
                "applications": {
                    "instances": {app_instance: {"class": "ods", "state": "RUN"}}
                }
            }
        )
        print("Configuration change successful!")
    except Exception as err:
        print(f"Error while changing a CONF parameter: {err}")

    print("ODS configuration with presets completed!")


if __name__ == "__main__":
    ip = "192.168.0.69"
    config_file = "configs/ods_two_heads_presets.json"
    main(ip, config_file)
