#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# %%
from datetime import datetime
import json
import logging
import numpy as np
from o3r_algo_utilities.calib import calibration

#############################
# Logger configuration
#############################
now = datetime.now()
logger = logging.getLogger(__name__)
# Switch this to False will not log to file
log_to_file = True
# Set log level
log_level = logging.INFO
if log_to_file:
    logging.basicConfig(
        filename=f'{now.strftime("%Y%m%d")}_{now.strftime("%H%M%S")}_satic_calib.log',
        level=log_level,
    )
else:
    logging.basicConfig(
        level=log_level,
    )

# %%
#############################
# Camera configuration values
# EDIT HERE
#############################
cam_port: int = 2
ip: str = "192.168.0.69"
# Horizontal: camera's long side is parallel to the floor plane
# Set horizontal_mounting = False when the camera is mounted vertically
horizontal_mounting: bool = True
# Right side up:
# label is on the top side of the camera if the camera is mounted horizontally,
# cable is pointing down if the camera is mounted vertically
upside_down: bool = False

logger.info(f"Camera port: {cam_port}")
logger.info(f"IP address: {ip}")
logger.info(f"Horizontal mounting: {horizontal_mounting}")
logger.info(f"Upside down: {upside_down}")


##################################
# Provide a translation estimation
# of the camera position in [m]
# EDIT HERE
##################################
# The 3 vector (tx,ty,tz) specifies
# the position of the head's reference point
# expressed in the robot coordinate system.
# For instance:
# fixed_translation = "[0.25, -0.1, 0.5]"
fixed_translation: str = None
logger.info(f"Fixed translation: {fixed_translation}")

############################################
# Size of the checkerboard.
# The variables are pre-filled with the
# dimensions of the default checkerboard.
# EDIT HERE
############################################
# The size of the white border around the checkerboard [m]
frame_size: float = 0.05
# Number of inner points (intersections of checkerboard cells) on target
target_width: int = 6
target_height: int = 4
# Sanity check on checkerboard size
if target_height <= 1 or target_width <= 1:
    raise ValueError("Target width and/or height should be above one.")
logger.info(
    f"Target size: {frame_size}, Width: {target_width}, Height: {target_height})"
)

###########################################
# XYZ coordinates [m] of the
# corners of the checkerboard (ABCD points)
# AB and CD are always the corners of the
#   long side of the checkerboard
# AC and BD are always the corners of the
#   short sides of the checkerboard
# EDIT HERE
###########################################
# Update these values to the values measured
# in your setup.
if horizontal_mounting:
    # A is upper left corner in the image and also in the world
    X_AB = 0.0
    Z_AB = 0.0
    X_CD = 0.0
    Z_CD = 0.0
    Y_AC = 0.0
    Y_BD = 0.0
    if upside_down:
        # Substitute corners coordinates for upside down camera mounting
        X_AB, X_CD = X_CD, X_AB
        Z_AB, Z_CD = Z_CD, Z_AB
        Y_AC, Y_BD = Y_BD, Y_AC

    logger.info(
        f"X_AB={X_AB},Z_AB={Z_AB},X_CD={X_CD},Z_CD={Z_CD},Y_AC={Y_AC},Y_BD={Y_BD}"
    )
    pcc = f"X_AB={X_AB},Z_AB={Z_AB},X_CD={X_CD},Z_CD={Z_CD},Y_AC={Y_AC},Y_BD={Y_BD}"
else:
    # Camera and target are mounted vertically
    # A is upper left corner in the image and lower left corner in the world
    X_AC = 0.0
    Z_AC = 0.0
    X_BD = 0.0
    Z_BD = 0.0
    Y_AB = 0.0
    Y_CD = 0.0

    logger.info(
        f"X_AC={X_AC},Z_AC={Z_AC},X_BD={X_BD},Z_BD={Z_BD},Y_AB={Y_AB},Y_CD={Y_CD}"
    )
    pcc = f"X_AC={X_AC},Z_AC={Z_AC},X_BD={X_BD},Z_BD={Z_BD},Y_AB={Y_AB},Y_CD={Y_CD}"

##################################
# Pick the data source
# and the image type
##################################
source = f"ifm3dpy://{ip}/port{cam_port}"
# Internal ifm use only:
# source = f"adlive://{ip}/port{cam_port}"
# it's also possible to use a recording as source:
# source=r"adrec://C:\Projects\iCV-Algo\O3R\workspace\20210920_095332_calib2.h5"

# Only switch to "reflectivity" if the calibration fails with the "amplitude".
# image_selection = "reflectivity"
image_selection = "amplitude"

# Pick the mode to set to the calibrated camera
# Switch to standard mode in cases where ambient light is too low
mode = "extrinsic_calib"
# mode = "standard_range2m"
logger.info(f"Image selection: {image_selection}")
logger.info(f"Mode: {mode}")

###########
# Calibrate
###########
args = dict(
    frame_size=frame_size,
    pattern_corner_coordinates=pcc,
    target_width=target_width,
    target_height=target_height,
    source=source,
    max_allowed_reconstruction_error=0.6,
    fixed_translation=fixed_translation,
    image_selection=image_selection,
    mode=mode,
)
trans, rot = calibration.calib(**args)

# %%
##########################################
# Log generated values and write to file
##########################################
logger.info(f"Generated translations: {trans}")
logger.info(f"Generated rotations: {rot}")
new_calib = {
        "ports": {
            f"port{cam_port}": {
                "processing": {
                    "extrinsicHeadToUser": dict(
                        rotX= np.round(rot[0], 3),
                        rotY= np.round(rot[1], 3),
                        rotZ= np.round(rot[2], 3),
                        transX= np.round(trans[0], 3),
                        transY= np.round(trans[1], 3),
                        transZ= np.round(trans[2], 3),
                    )
                }
            }
        }
    }
with open(
    f'{now.strftime("%Y%m%d")}_{now.strftime("%H%M%S")}_calib_cam_port{cam_port}.json',
    "w",
) as out_file:
    json.dump(new_calib, out_file, indent=4)
    logger.info(f"Generated calibration json dumped in {out_file.name}")


# %%
###########################################
# Push the calibrated values to the device.
###########################################
if ip is not None:
    from ifm3dpy.device import O3R

    o3r = O3R(ip)
    o3r.reset(f"/ports/port{cam_port}/mode")
    old_calib = o3r.get([f"/ports/port{cam_port}/processing/extrinsicHeadToUser"])
    logger.info(
        "old_calib= %s",
        old_calib["ports"][f"port{cam_port}"]["processing"]["extrinsicHeadToUser"],
    )
    try:
        o3r.set(new_calib)
    except Exception as e:
        raise e
    finally:
        new_calib = o3r.get([f"/ports/port{cam_port}/processing/extrinsicHeadToUser"])
        logger.info("Check the new calibration values")
        logger.info(
            "Cam port%d new_calib=%s",
            cam_port,
            new_calib["ports"][f"port{cam_port}"]["processing"]["extrinsicHeadToUser"],
        )
