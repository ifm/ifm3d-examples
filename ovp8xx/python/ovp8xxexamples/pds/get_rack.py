#!/usr/bin/env python3
###########################################
###2023-present ifm electronic, gmbh
###SPDX-License-Identifier: Apache-2.0
###########################################

"""
Setup:  * Camera: O3R222, 3D on port0
            * orientation: camera horizontally (FAKRA cable to the left)
        * Rack: rack in FoV @ 1.5m distance
"""
import json
import logging
import time
import numpy as np

from ifm3dpy.device import O3R, Error
from ifm3dpy.framegrabber import FrameGrabber, buffer_id

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Device specific configuration
IP = "192.168.0.69"
CAMERA_PORT = "port0"
APP_PORT = "app0"
o3r = O3R(IP)

############################################
# Setup the application
############################################
try:
    o3r.reset("/applications/instances")
except Error as e:
    logger.info(f"Reset failed: {e}")

# Set the correct extrinsic calibration of the camera.
calibration = {
    "transX": 0.0,
    "transY": 0.0,
    "transZ": 0.2,
    "rotX": 0.0,
    "rotY": 1.57,
    "rotZ": -1.57,
}
logger.info(f"Setting the extrinsic calibration for camera in {CAMERA_PORT}")
o3r.set({"ports": {CAMERA_PORT: {"processing": {"extrinsicHeadToUser": calibration}}}})

# Create the application instance and set to IDLE (ready to be triggered)
logger.info(f"Create a PDS instance using camera in {CAMERA_PORT}")
o3r.set(
    {
        "applications": {
            "instances": {
                APP_PORT: {"class": "pds", "ports": [CAMERA_PORT], "state": "IDLE"}
            }
        }
    }
)

############################################
# Setup the framegrabber to receive frames
# when the application is triggered.
############################################
fg = FrameGrabber(o3r, o3r.port(APP_PORT).pcic_port)
fg.start([buffer_id.O3R_RESULT_JSON])


# Define a callback function to be executed every time a frame is received
def rack_callback(frame):
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
        logger.info(f"Detected rack: {parsed_json_array['getRack']}")


fg.on_new_frame(rack_callback)

############################################
# Trigger the getRack command
############################################
time.sleep(2)  # Grace period after the framegrabber starts

GET_RACK_PARAMETERS = {
    "depthHint": 1.2,  # Estimated position of the rack (-1 for automatic detection)
    "horizontalDropPosition": "left",
    "verticalDropPosition": "interior",
    "zHint": -0.4,
}

logger.info("Triggering the getRack command")
o3r.set(
    {
        "applications": {
            "instances": {
                APP_PORT: {
                    "configuration": {
                        "customization": {
                            "command": "getRack",
                            "getRack": GET_RACK_PARAMETERS,
                        }
                    }
                }
            }
        }
    }
)

# Allow time for the callback to execute before exiting
time.sleep(3)
fg.stop()
