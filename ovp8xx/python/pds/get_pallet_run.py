# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This script is configuring an PDS application with one camera plugged to the port2
# It is assumed that the camera is mounted horizontally with the label facing upward.
# The default camera height is 35 cm, but this can be modified in the config file.

import json
import pathlib
import time
from queue import Queue
from threading import Thread

import numpy as np
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import Frame, FrameGrabber, buffer_id

# Initialize a queue to store results
result_queue = Queue(maxsize=1)


def async_diagnostic_callback(message: str, app_name: str) -> None:
    """Diagnostic callback function to handle asynchronous diagnostic messages.
    This function is called when a new diagnostic message is received.

    Args:
        message (str): The diagnostic message received from the O3R device.
        app_name (str): The name of the application instance to check the status for.
    """
    try:
        diagnostic = json.loads(message)
    except json.JSONDecodeError:
        print(f"Failed to decode JSON message: {message}")
        return

    groups = diagnostic.get("groups", {})
    app_status = groups.get(app_name, "unknown")

    if app_status != "not_available" and app_status != "no_incident":
        print(f"\nNew Diagnostic: The status of application '{app_name}': {app_status}")
        if app_status == "critical":
            print(
                f"⚠️ Application '{app_name}' is in a critical state! Stop the Robot!!"
            )


def callback(frame: Frame) -> None:
    """Callback function executed every time a frame is received.
    The data is decoded and the result printed.

    :param frame: A frame containing the data for all the buffer ids
    requested in the start function of the framegrabber.
    """
    if frame.has_buffer(buffer_id.O3R_RESULT_JSON):
        json_chunk = frame.get_buffer(buffer_id.O3R_RESULT_JSON)
        json_array = np.frombuffer(json_chunk[0], dtype=np.uint8)
        json_array = json_array.tobytes()
        parsed_json_array = json.loads(json_array.decode())
        result_queue.put(parsed_json_array["getPallet"])


def process_queue() -> None:
    """Function to process the result queue and display the output."""
    while True:
        if not result_queue.empty():
            result = result_queue.get()
            print(f"Detected pallet(s): {json.dumps(result, indent=4)}")
            # Do something with the result

        time.sleep(0.1)  # Avoid busy-waiting


def main(ip: str, extrinsics_config: str, app_config: str) -> None:
    """Main function to get pallet pose from PDS application

    Args:
        ip (str): IP address of the O3R system
        config_file (str): path to the configuration file
    """
    o3r = O3R(ip)

    # Reset the application instances to ensure a clean state
    try:
        o3r.reset("/applications/instances")
    except Exception as e:
        print(f"Reset failed: {e}")

    # Load multiple configuration files
    actual_path = pathlib.Path(__file__).parent.resolve()
    try:
        with open(
            actual_path / app_config, "r", encoding="utf-8"
        ) as app_config_file, open(
            actual_path / extrinsics_config, "r", encoding="utf-8"
        ) as extrinsics_config_file:
            pds_configuration = json.load(app_config_file)
            extrinsics_configuration = json.load(extrinsics_config_file)
    except FileNotFoundError as e:
        print(f"Configuration file not found: {e.filename}. Exiting.")
        return
    except json.JSONDecodeError as e:
        print(f"Failed to parse configuration file: {e.msg}. Exiting.")
        return

    # Retrieve app_instance from configuration file
    app_instance = next(iter(pds_configuration["applications"]["instances"]))

    # Start diagnostic monitoring with a separate FrameGrabber
    diagnostics_fg = FrameGrabber(o3r, o3r.port("diagnostics").pcic_port)
    diagnostics_fg.on_async_error(
        callback=lambda id, message: async_diagnostic_callback(message, app_instance)
    )
    print("Starting async diagnostic monitoring. ")
    diagnostics_fg.start([])

    # Set the configuration
    print("Setting Extrinsics configuration")
    o3r.set(extrinsics_configuration)

    print("Setting PDS configuration")
    o3r.set(pds_configuration)

    # Create framegrabber instance for application port
    application_fg = FrameGrabber(o3r, o3r.port(f"{app_instance}").pcic_port)
    application_fg.start([buffer_id.O3R_RESULT_JSON])
    application_fg.on_new_frame(callback)

    # Set the PDS application to the RUN state
    print("Setting PDS application to RUN state")
    o3r.set({"applications": {"instances": {f"{app_instance}": {"state": "RUN"}}}})

    # Start a thread to process the queue
    queue_thread = Thread(target=process_queue, daemon=True)
    queue_thread.start()

    # Edit the getPallet parameters as needed
    GET_PALLET_PARAMETERS = {
        "depthHint": 0,  # 0 = Auto depthHint
        "palletIndex": 0,  # 0 = EPAL pallet
        "palletOrder": "zDescending",  # zDescending = Detected Pallets order
    }

    # Trigger the PDS Application to detect pallet(s)
    print("Triggering PDS application to detect pallet(s)")

    # Trigger the PDS Application to detect pallet(s)
    o3r.set(
        {
            "applications": {
                "instances": {
                    f"{app_instance}": {
                        "configuration": {
                            "customization": {
                                "command": "getPallet",
                                "getPallet": GET_PALLET_PARAMETERS,
                            }
                        }
                    }
                }
            }
        }
    )

    time.sleep(3)

    # Stop the framegrabber(s)
    diagnostics_fg.stop()
    application_fg.stop()


if __name__ == "__main__":
    IP = "192.168.0.69"
    EXTRINSICS_CONFIG_FILE = "configs/extrinsics.json"
    APP_CONFIG_FILE = "configs/pds_getPallet.json"
    main(
        ip=IP,
        extrinsics_config=EXTRINSICS_CONFIG_FILE,
        app_config=APP_CONFIG_FILE,
    )
