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
#############################
cam_port = 2
ip = "192.168.0.69"
# Horizontal: camera's long side is parallel to the floor plane
# Set horizontal_mounting = False when the camera is mounted vertically
horizontal_mounting = True
# Right side up:
# label is on the top side of the camera if the camera is mounted horizontally,
# cable is pointing down if the camera is mounted vertically
upside_down = False
logger.info(f"Camera port: {cam_port}")
logger.info(f"IP address: {ip}")
logger.info(f"Horizontal mounting: {horizontal_mounting}")
logger.info(f"Upside down: {upside_down}")

##########################
# Size of the checkerboard
##########################
# The size of the white border around the checkerboard [m]
frame_size = 0.05
# Number of inner points (intersections of checkerboard cells) on target
target_width = 6
target_height = 4
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
###########################################
if horizontal_mounting:
    # A is upper left corner in the image and also in the world
    X_AB = 0.4
    Z_AB = 0.49
    X_CD = 0.08
    Z_CD = 0
    Y_AC = 0.8
    Y_BD = 0
    ##################################################
    # If checkerboard is sideways (parallel to X axis):
    # use these variables instead
    ##################################################
    # X_AC=0
    # X_BD=0
    # Y_AB=0
    # Y_CD=0
    # Z_AB=0
    # Z_CD=0
    if upside_down:
        # Substitute corners coordinates for upside down camera mounting
        X_AB, X_CD = X_CD, X_AB
        Y_AC, Y_BD = Y_BD, Y_AC
        Z_AB, Z_CD = Z_CD, Z_AB
        # If the checkerboard is sideways:
        # X_AC, X_BD = X_BD, X_AC
        # Y_AB, Y_CD = Y_CD, Y_AB
        # Z_AB, Z_CD = Z_CD, Z_AB

    logger.info(
        f"X_AB={X_AB},Z_AB={Z_AB},X_CD={X_CD},Z_CD={Z_CD},Y_AC={Y_AC},Y_BD={Y_BD}"
    )
    pcc = f"X_AB={X_AB},Z_AB={Z_AB},X_CD={X_CD},Z_CD={Z_CD},Y_AC={Y_AC},Y_BD={Y_BD}"
    # If the checkerboard is sideways:
    # logger.info(
    #     f"X_AC={X_AC},Z_AB={Z_AB},X_BD={X_BD},Z_CD={Z_CD},Y_AB={Y_AB},Y_CD={Y_CD}"
    # )
    # pcc = f"X_AC={X_AC},Z_AB={Z_AB},X_BD={X_BD},Z_CD={Z_CD},Y_AB={Y_AB},Y_CD={Y_CD}"
else:
    # Camera and target are mounted vertically
    # A is upper left corner in the image and lower left corner in the world
    X_AC = 1.227 - 0.057
    X_BD = 1.227
    Y_AB = 0.3
    Y_CD = -0.3
    Z_AC = 0.0
    Z_BD = 0.798
    logger.info(
        f"X_AC={X_AC},Z_AC={Z_AC},X_BD={X_BD},Z_BD={Z_BD},Y_AB={Y_AB},Y_CD={Y_CD}"
    )
    pcc = f"X_AC={X_AC},Z_AC={Z_AC},X_BD={X_BD},Z_BD={Z_BD},Y_AB={Y_AB},Y_CD={Y_CD}"
    ##################################################
    # If checkerboard is sideways (parallel to X axis):
    # use these variables instead
    ##################################################
    # X_AB=0
    # X_CD=0
    # Y_AC=0
    # Y_BD=0
    # Z_AC=0
    # Z_BD=0
    # logger.info(
    #     f"X_AB={X_AB},Z_AC={Z_AC},X_CD={X_CD},Z_BD={Z_BD},Y_AC={Y_AC},Y_BD={Y_BD}"
    # )
    # pcc = f"X_AB={X_AB},Z_AC={Z_AC},X_CD={X_CD},Z_BD={Z_BD},Y_AC={Y_AC},Y_BD={Y_BD}"

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

##################################
# If available,
# provide a translation estimation
# of the camera position in [m]
##################################
# The 3 vector (tx,ty,tz) specifies
# the position of the head's reference point
# expressed in the robot coordinate system.
# For instance:
# fixed_translation = [0.25, -0.1, 0.5]
fixed_translation = None
logger.info(f"Fixed translation: {fixed_translation}")

###########
# Calibrate
###########
args = dict(
    frame_size=frame_size,
    pattern_corner_coordinates=pcc,
    target_width=target_width,
    target_height=target_height,
    source=source,
    max_allowed_reconstruction_error=2,
    fixed_translation=fixed_translation,
    image_selection=image_selection,
    mode=mode,
)
trans, rot = calibration.calib(**args)

# %%
##########################################
# Print generated values and write to file
##########################################
print(trans, rot)
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
    from ifm3dpy import O3R

    o3r = O3R(ip)
    old_calib = o3r.get([f"/ports/port{cam_port}/processing/extrinsicHeadToUser"])
    logger.info(
        "old_calib= %s",
        old_calib["ports"][f"port{cam_port}"]["processing"]["extrinsicHeadToUser"],
    )
    # Changing the mode together with the extrinsic calibration
    # to avoid configuration issues
    new_calib["ports"][f"port{cam_port}"]["mode"]  = "cyclic_4m_2m_4m_2m"
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
