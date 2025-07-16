# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This script is calibrating a camera using
# the SCC embedded application.
# The calibration routine is triggered by sending the
# "calibrate" command to the SCC application with the
# set command, in JSON.
# The result is received in the O3R_RESULT_JSON buffer,
# through the registered callback.
# The "writeToDevice" command can be sent to set
# the generated calibration values to the port.

import json
import pathlib

import numpy as np
from ifm3dpy.device import O3R, Error
from ifm3dpy.framegrabber import FrameGrabber, buffer_id

# Global variable to track calibration status
CALIBRATED = False


def load_config(config_path):
    """Load configuration from a JSON file."""
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except OSError as err:
        print("Error while reading configuration file")
        raise err


def calibration_callback(frame):
    """Callback to process received calibration results."""
    global CALIBRATED
    if frame.has_buffer(buffer_id.O3R_RESULT_JSON) and not CALIBRATED:
        json_chunk = frame.get_buffer(buffer_id.O3R_RESULT_JSON)
        json_array = np.frombuffer(json_chunk[0], dtype=np.uint8).tobytes()
        parsed_json_array = json.loads(json_array.decode())
        # Check the calibrationState value
        calibration_state = parsed_json_array.get("calibrationState", 0)
        if calibration_state == 1:
            CALIBRATED = True
            print("Calibration successful!")
            print(json.dumps(parsed_json_array, indent=4))  # Pretty-print JSON


def send_command(o3r, app_instance, command):
    """Send a command to the application."""
    try:
        o3r.set(
            {
                "applications": {
                    "instances": {app_instance: {"configuration": {"command": command}}}
                }
            }
        )
        print(f"Command '{command}' sent successfully")
    except Error as err:
        print(f"Error while sending command '{command}'")
        raise err


def main(ip, config_file):
    global CALIBRATED
    # Initialize O3R device
    o3r = O3R(ip)

    # Load configuration
    config_path = pathlib.Path(__file__).parent / config_file
    config_snippet = load_config(config_path)
    app_instance = next(iter(config_snippet["applications"]["instances"]))
    print(f"Using application instance: {app_instance}")

    # Ensure a clean start, only reseting the instance we are using
    try:
        current_instances = o3r.get(["/applications/instances"])["applications"]
        if current_instances is not None:
            instances = current_instances["instances"].keys()
            if app_instance in instances:
                o3r.reset("/applications/instances/" + app_instance)
                print(f"Reset application instance: {app_instance}")
            else:
                print(
                    f"Application instance '{app_instance}' not found, skipping reset."
                )
        else:
            print("No application instances found, skipping reset.")
    except Error as e:
        print(f"Reset failed: {e}")

    # Apply configuration
    try:
        o3r.set(config_snippet)
        print("Configuration applied successfully")
    except Error as err:
        print("Error while applying configuration")
        raise err

    # Set application to RUN state
    try:
        o3r.set(
            {
                "applications": {
                    "instances": {app_instance: {"class": "scc", "state": "RUN"}}
                }
            }
        )
        print("Application set to RUN state")
    except Error as err:
        print("Error while setting application to RUN state")
        raise err

    # Clear the buffer before calibration to not have any old data
    send_command(o3r, app_instance, "clearBuffer")

    # Setup framegrabber
    fg = FrameGrabber(o3r, o3r.port(app_instance).pcic_port)
    fg.start([buffer_id.O3R_RESULT_JSON])
    fg.on_new_frame(calibration_callback)

    send_command(o3r, app_instance, "calibrate")

    if CALIBRATED:
        print("Calibration successful, writing to device...")
        # Write calibration to device
        send_command(o3r, app_instance, "writeToDevice")
    else:
        print("Calibration failed, please check the camera setup.")

    # stop framegrabber
    fg.stop()


if __name__ == "__main__":
    ip = "192.168.0.69"
    config_file = "config/scc_calibration_port2_with_translations.json"
    main(ip, config_file)
