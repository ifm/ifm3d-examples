#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
"""This module shows how to use the o3r_algo_utilities package to convert Euler angles between O3R2XX format and human-readable format.

The module performs the following tasks:
- Retrieves the current calibration for a specific camera port of an O3R device.
- Converts the O3R2XX Euler angles to human-readable angles.
- Converts human-readable angles to O3R2XX Euler angles.
- Sets the new calibration for the camera port.

To use this module, you need to edit the IP address and camera port for your device.

WARNING: this code will edit the configuration of your device.
"""
import numpy as np
from o3r_algo_utilities.rotmat import (
    o3rCalibAnglesToHumanReadable,
    humanReadableToO3RCalibAngles,
)
from ifm3dpy.device import O3R

# HERE edit the IP address for your device and the camera port
IP = "192.168.0.69"
CAMERA_PORT = "port0"

# Collect the current calibration for the port
o3r = O3R(IP)
calib_cam = o3r.get([f"/ports/{CAMERA_PORT}/processing/extrinsicHeadToUser"])["ports"][
    CAMERA_PORT
]["processing"]["extrinsicHeadToUser"]
euler_rot = np.array([calib_cam["rotX"], calib_cam["rotY"], calib_cam["rotZ"]])


# %%##############################
# Convert O3R2XX Euler angles to
# human readable angles
#################################
human_read_angles = o3rCalibAnglesToHumanReadable(*euler_rot)

# %%##############################
# Convert human readable angles to
# O3R22X Euler angles
#################################
# Let's say we want to rotate the O3R22X to facing forward in a
# typical robot coordinate system, where X is forward, Y is to the
# left, and Z is up.
# Camera coordinate system for O3R22X is X following the connector direction,
# Y in the direction opposite of the printed label and Z forward.
# We need to rotate the camera frame to the world frame.
# Roll, pitch and yaw are expressed in the world frame.
ROLL = 0  # degrees
PITCH = 0
YAW = 0

euler_rot = humanReadableToO3RCalibAngles(roll=ROLL, pitch=PITCH, yaw=YAW)

# Setting the new calibration
o3r.set(
    {
        "ports": {
            CAMERA_PORT: {
                "processing": {
                    "extrinsicHeadToUser": {
                        "rotX": euler_rot[0],
                        "rotY": euler_rot[1],
                        "rotZ": euler_rot[2],
                    }
                }
            }
        }
    }
)
# %%
