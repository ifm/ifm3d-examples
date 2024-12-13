#!/usr/bin/env python3
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
"""The flags provide additional information for each pixel 
in the image, in a similar way as the confidence image for 
the O3R camera. The flags are stored in the ifm3d buffer
O3R_RESULT_ARRAY2D.
To retrieve flags, a command must be triggered (we use
the getPallet command in this example).
"""
# %%
import logging
import time
from ifm3dpy.device import O3R, Error
from ifm3dpy.framegrabber import FrameGrabber, buffer_id

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# %% Edit for the IP address of your OVP8xx and the camera port
IP = "192.168.0.69"
CAMERA_PORT = "port0"
APP_PORT = "app0"
o3r = O3R(IP)

# %%#########################################
# Setup the application
############################################
# Ensure a clean slate before running the example
try:
    o3r.reset("/applications/instances")
except Error as e:
    logger.error(f"Reset failed: {e}")

# Set the extrinsic calibration of the camera
calibration = {
    "transX": 0.0,
    "transY": 0,
    "transZ": 0.0,
    "rotX": -1.57,
    "rotY": 1.57,
    "rotZ": 0,
}
logger.info(f"Setting extrinsic calibration for {CAMERA_PORT}")
o3r.set({"ports": {CAMERA_PORT: {"processing": {"extrinsicHeadToUser": calibration}}}})

# Create the PDS application and
# choose the camera port
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

# %%#########################################
# Setup the framegrabber to receive frames
# when the application is triggered.
############################################
fg = FrameGrabber(o3r, o3r.port(APP_PORT).pcic_port)
fg.start([buffer_id.O3R_RESULT_ARRAY2D])


# Define a callback to be executed when a frame is received
def flags_callback(frame):
    """Callback to be executed for each received pallet frame.
    Retrieve the data from the corresponding buffer and
    deserialize it into a JSON array.
    :param frame: the result of the getPallet command.
    """
    if frame.has_buffer(buffer_id.O3R_RESULT_ARRAY2D):
        flags = frame.get_buffer(buffer_id.O3R_RESULT_ARRAY2D)
        logger.info(f"Pixel flags: {flags}")
        logger.info(f"Flag fox pixel (100, 100): {flags[100, 100]}")


fg.on_new_frame(flags_callback)

# %%#########################################
# Trigger the getPallet command: we need to
# trigger a command to retrieve the corresponding
# flags for each pixel in the image.
############################################
time.sleep(2)
GET_PALLET_PARAMETERS = {
    "depthHint": -1,
    "palletIndex": 0,  # Block Pallet/EPAL pallet
}

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

# %% Stop the framegrabber
fg.stop()
