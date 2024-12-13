###########################################
###2023-present ifm electronic, gmbh
###SPDX-License-Identifier: Apache-2.0
###########################################
"""
Setup:  * Camera: O3R222, 3D on port0 
            * orientation: camera horizontally (Fakra cable to the left, label up)
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

calibration = {
    "transX": 0.0,
    "transY": 0.0,
    "transZ": 0.2,  # 20 cm above the ground
    "rotX": 0,
    "rotY": 1.57,  # rotY and rotZ define camera horizontal and looking straight forward
    "rotZ": -1.57,
}
logger.info(f"Setting the calibration for camera in {CAMERA_PORT}")
o3r.set({"ports": {CAMERA_PORT: {"processing": {"extrinsicHeadToUser": calibration}}}})

logger.info(f"Create a PDS instance using the camera in {CAMERA_PORT}")
o3r.set(
    {
        "applications": {
            "instances": {
                APP_PORT: {"class": "pds", "ports": [CAMERA_PORT], "state": "IDLE"}
            }
        }
    }
)

time.sleep(0.5)
############################################
# Setup the framegrabber to receive frames
# when the application is triggered.
############################################
fg = FrameGrabber(o3r, o3r.port(APP_PORT).pcic_port)
fg.start([buffer_id.O3R_RESULT_JSON])


def volume_callback(frame):
    """Callback method called every time a frame is received.
    Deserialize the data from the result of the volCheck command.

    :param frame: frame containing the results of the volCheck command
    """
    if frame.has_buffer(buffer_id.O3R_RESULT_JSON):
        json_chunk = frame.get_buffer(buffer_id.O3R_RESULT_JSON)
        json_array = np.frombuffer(json_chunk[0], dtype=np.uint8)
        json_array = json_array.tobytes()
        parsed_json_array = json.loads(json_array.decode())
        logger.info(
            f"Number of pixels in the volume: {parsed_json_array['volCheck']['numPixels']}"
        )


fg.on_new_frame(volume_callback)

############################################
# Trigger the volCheck command
############################################
time.sleep(2)  # Grace period after the framegrabber starts

# Define the boudaries of the volume to be checked
VOLCHECK_PARAMETERS = {
    "xMin": 1,
    "xMax": 2,
    "yMin": -0.5,
    "yMax": 0.5,
    "zMin": 0.0,
    "zMax": 0.4,
}

logger.info("Triggering the volCheck command")
o3r.set(
    {
        "applications": {
            "instances": {
                APP_PORT: {
                    "configuration": {
                        "customization": {
                            "command": "volCheck",
                            "volCheck": VOLCHECK_PARAMETERS,
                        }
                    }
                }
            }
        }
    }
)

time.sleep(3)
fg.stop()
