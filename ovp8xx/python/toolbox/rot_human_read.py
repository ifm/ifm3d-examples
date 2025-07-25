# -*- coding: utf-8 -*-
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
from ifm3dpy.device import O3R
from o3r_algo_utilities.rotmat import (
    humanReadableToO3RCalibAngles,
    o3rCalibAnglesToHumanReadable,
)


def main(ip, port):
    # Collect the current calibration for the port
    o3r = O3R(ip)
    calib_cam = o3r.get([f"/ports/{port}/processing/extrinsicHeadToUser"])["ports"][
        port
    ]["processing"]["extrinsicHeadToUser"]
    euler_rot = np.array([calib_cam["rotX"], calib_cam["rotY"], calib_cam["rotZ"]])

    # %%##############################
    # Convert O3R2XX Euler angles to
    # human readable angles
    #################################
    human_read_angles = o3rCalibAnglesToHumanReadable(*euler_rot)
    print(
        f"Human readable angles equivalent to the current calibration values (degrees): {human_read_angles}"
    )

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
    YAW = 0  # degrees
    PITCH = 0
    ROLL = 0

    euler_rot = humanReadableToO3RCalibAngles(yaw=YAW, pitch=PITCH, roll=ROLL)
    print(f"O3R2XX angles, camera facing forward (radians): {euler_rot}")

    # Now let's say the camera is facing to the left,
    # that is, the camera is rotated 90 degrees around the Z axis.
    YAW = 90  # degrees
    PITCH = 0
    ROLL = 0

    euler_rot = humanReadableToO3RCalibAngles(yaw=YAW, pitch=PITCH, roll=ROLL)
    print("O3R2XX angles, camera facing to the left (radians):", euler_rot)


# %%
if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
        PORT = config.PORT_3D

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        PORT = "port2"

    main(ip=IP, port=PORT)
