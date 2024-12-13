#!/usr/bin/env python3
###########################################
###2023-present ifm electronic, gmbh
###SPDX-License-Identifier: Apache-2.0
###########################################
"""
Setup:  * Camera: O3R222, 3D on port 0 
            * orientation: camera horizontally oriented (label up, Fakra cable to the left)
        * Pallet: pallet in FoV @ 1.5m distance from the camera
"""
# %%
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
# Ensure a clean slate before running the example
try:
    o3r.reset("/applications/instances")
except Error as e:
    logger.info(f"Reset failed: {e}")

# Set the extrinsic calibration of the camera
calibration = {
    "transX": 0.0,
    "transY": 0.0,
    "transZ": 0.2,
    "rotX": 0.0,
    "rotY": 1.57,
    "rotZ": -1.57,
}
logger.info(f"Setting extrinsic calibration for {CAMERA_PORT}")
o3r.set({"ports": {CAMERA_PORT: {"processing": {"extrinsicHeadToUser": calibration}}}})

logger.info(f"Creating a PDS instance with camera in {CAMERA_PORT}")
o3r.set(
    {
        "applications": {
            "instances": {
                APP_PORT: {"class": "pds", "ports": [CAMERA_PORT], "state": "IDLE"}
            }
        }
    }
)

# %%
############################################
# Setup the framegrabber to receive frames
# when the application is triggered.
############################################
fg = FrameGrabber(o3r, o3r.port(APP_PORT).pcic_port)
fg.start([buffer_id.O3R_RESULT_JSON])


# Define a callback to be executed when a frame is received
def pallet_callback(frame):
    """Callback to be executed for each received pallet frame.
    Retrieve the data from the corresponding buffer and
    deserialize it into a JSON array.
    :param frame: the result of the getPallet command.
    """
    if frame.has_buffer(buffer_id.O3R_RESULT_JSON):
        json_chunk = frame.get_buffer(buffer_id.O3R_RESULT_JSON)
        json_array = np.frombuffer(json_chunk[0], dtype=np.uint8)
        json_array = json_array.tobytes()
        parsed_json_array = json.loads(json_array.decode())
        logger.info(f"Detected pallet(s): {parsed_json_array['getPallet']['pallet']}")


fg.on_new_frame(pallet_callback)

############################################
# Trigger the getPallet command
############################################

# Provide the estimated distance to the pallet and the pallet type.
GET_PALLET_PARAMETERS = {
    "depthHint": 1.2,  # We recommend providing a depth hint for faster detections
    "palletIndex": 0,  # Block Pallet/EPAL pallet
}

# %%
logger.info("Triggering the getPallet command")
o3r.set(
    {
        "applications": {
            "instances": {
                APP_PORT: {
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
# Sleep to ensure we have time to execute the callback before exiting.
time.sleep(3)
# %%
fg.stop()
