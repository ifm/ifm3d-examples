#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This module provides an example on how to register the 2D and 3D
# images of a single camera head to obtain a colored point cloud.
# Frames are acquired continuously until the user presses 'S' to
# save a specific frame. The registration will be done in this
# one frame. Registering the 2D and 3D data continuously is
# left as an exercise for the user.

# This file can be run interactively, section by section in sequential order:
# Sections are delimited by '#%%'
# Several editors including Spyder and vscode+python are equipped to run these cells
# by simply pressing shift-enter

# %%
from datetime import datetime
from pathlib import Path
import os
import cv2
import matplotlib.pyplot as plt
import open3d as o3d
import numpy as np
from o3r_algo_utilities.rotmat import rotMat, rotMatReverse
from o3r_algo_utilities.o3r_uncompress_di import evalIntrinsic
from o3r_algo_utilities.calib.point_correspondences import inverse_intrinsic_projection


# %%##########################################
# Define camera ports and VPU IP address
# CONFIGURE FOR YOUR SETUP
############################################
IP_ADDR = "192.168.0.69"  # This is the default address
PORT2D = "port0"
PORT3D = "port2"

############################################
# Read data from file or use live data
############################################
USE_RECORDED_DATA = True
# Enter file name when using the replay mode.
# If multiple frames are available in the file,
# then the first frame will be used.
FILE_NAME = "test_rec.h5"
# Show 3D cloud or not.
SHOW_OPEN3D = True


def check_heads_requirements(config: dict):
    """Verifies that the provided ports can be used for registration.

    :param config: the full json configuration of the device being used.
    :raises ValueError: if the provided ports fo not belong to the same camera head.
    :raises ValueError: if the provided ports are calibrated with different values.
    """
    # Check that ports from the same camera head are provided
    if (
        config["ports"][PORT2D]["info"]["serialNumber"]
        != config["ports"][PORT3D]["info"]["serialNumber"]
    ):
        raise ValueError("2D and 3D ports must belong to the same camera head.")

    if (
        config["ports"][PORT2D]["processing"]["extrinsicHeadToUser"]
        != config["ports"][PORT3D]["processing"]["extrinsicHeadToUser"]
    ):
        raise ValueError(" 2D and 3D ports should have the same extrinsic calibration")

    if (
        config["ports"][PORT2D]["info"]["features"]["type"]
        == config["ports"][PORT3D]["info"]["features"]["type"]
    ):
        raise ValueError("The ports must have different types.")


# %%#########################################
# Load pre-recorded data in ifm h5 format,
# for example recorded with the ifm Vision Assistant
############################################
if USE_RECORDED_DATA:
    import h5py
    import json

    class ExtrinsicOpticToUser:
        def __init__(self) -> None:
            self.trans_x = 0.0
            self.trans_y = 0.0
            self.trans_z = 0.0
            self.rot_x = 0.0
            self.rot_y = 0.0
            self.rot_z = 0.0

    # TODO: Remove the path parent resolve to just provide full path to h5py.File
    current_dir = Path(__file__).parent.resolve()

    # Unpack all data required to 2d3d registration
    hf1 = h5py.File(str(current_dir / FILE_NAME), "r")

    config = json.loads(hf1["streams"]["o3r_json"]["data"][0].tobytes())
    try:
        check_heads_requirements(config=config)
    except ValueError as e:
        raise ValueError(e)

    # If the recording contains data from more than one head,
    # pick the proper stream (it might be "o3r_rgb_1" and "o3r_tof_1")
    # TODO: name of stream depends on the number of 3D ports connected. Probably deserves a Polarion issue.
    rgb = hf1["streams"]["o3r_rgb_1"]
    tof = hf1["streams"]["o3r_tof_1"]

    jpg = rgb[0]["jpeg"]
    jpg = cv2.imdecode(jpg, cv2.IMREAD_UNCHANGED)
    jpg = cv2.cvtColor(jpg, cv2.COLOR_BGR2RGB)
    modelID2D = rgb[0]["intrinsicCalibModelID"]
    intrinsic2D = rgb[0]["intrinsicCalibModelParameters"]
    invModelID2D = rgb[0]["invIntrinsicCalibModelID"]
    invIntrinsic2D = rgb[0]["invIntrinsicCalibModelParameters"]
    extrinsicO2U2D = ExtrinsicOpticToUser()
    extrinsicO2U2D.trans_x = rgb[0]["extrinsicOpticToUserTrans"][0]
    extrinsicO2U2D.trans_y = rgb[0]["extrinsicOpticToUserTrans"][1]
    extrinsicO2U2D.trans_z = rgb[0]["extrinsicOpticToUserTrans"][2]
    extrinsicO2U2D.rot_x = rgb[0]["extrinsicOpticToUserRot"][0]
    extrinsicO2U2D.rot_y = rgb[0]["extrinsicOpticToUserRot"][1]
    extrinsicO2U2D.rot_z = rgb[0]["extrinsicOpticToUserRot"][2]
    extrinsic2D = config["ports"][PORT2D]["processing"]["extrinsicHeadToUser"]

    dis = tof[0]["distance"]
    amp = tof[0]["amplitude"]
    modelID3D = tof[0]["intrinsicCalibModelID"]
    intrinsics3D = tof[0]["intrinsicCalibModelParameters"]
    invModelID3D = tof[0]["invIntrinsicCalibModelID"]
    invIntrinsics3D = tof[0]["invIntrinsicCalibModelParameters"]
    extrinsicO2U3D = ExtrinsicOpticToUser()
    extrinsicO2U3D.trans_x = tof[0]["extrinsicOpticToUserTrans"][0]
    extrinsicO2U3D.trans_y = tof[0]["extrinsicOpticToUserTrans"][1]
    extrinsicO2U3D.trans_z = tof[0]["extrinsicOpticToUserTrans"][2]
    extrinsicO2U3D.rot_x = tof[0]["extrinsicOpticToUserRot"][0]
    extrinsicO2U3D.rot_y = tof[0]["extrinsicOpticToUserRot"][1]
    extrinsicO2U3D.rot_z = tof[0]["extrinsicOpticToUserRot"][2]
    extrinsic3D = config["ports"][PORT3D]["processing"]["extrinsicHeadToUser"]
    hf1.close()

# ###########################################
# Live data from connected o3r system
# ###########################################
else:
    from ifm3dpy.device import O3R

    from ovp8xxexamples.toolbox.collect_calibrations import PortCalibrationCollector
    from ovp8xxexamples.toolbox.loop_to_collect_frame import FrameCollector

    o3r = O3R(IP_ADDR)
    config = o3r.get()

    camera_ports = [PORT2D, PORT3D]
    try:
        check_heads_requirements(config=config)
    except ValueError as e:
        raise ValueError(e)
    ############################################
    # Collect port info and retrieve and unpack
    # the calibration data for each requested port.
    ############################################
    # TODO: Get rid of frame collector and just loop to collect calib for all ports
    ports_info = {
        camera_ports[i]: o3r.port(camera_ports[i]) for i in range(0, len(camera_ports))
    }
    ports_calibs = {
        ports_info[port_n]
        .port: PortCalibrationCollector(o3r, ports_info[port_n])
        .collect()
        for port_n in camera_ports
    }

    ###########################################
    # Record sample frames for registration
    #############################################
    frame_collector = FrameCollector(o3r, ports=camera_ports)
    frame_collector.loop()

    # Close any remaining opencv windows
    cv2.destroyAllWindows()

    # Unpack all data relevent to 2d3d registration
    most_recent_saved_buffers = frame_collector.saved_buffer_sets[-1]
    jpg = most_recent_saved_buffers[PORT2D]["rgb"]
    jpg = cv2.cvtColor(jpg, cv2.COLOR_BGR2RGB)
    dis = most_recent_saved_buffers[PORT3D]["dist"]
    amp = most_recent_saved_buffers[PORT3D]["NAI"]
    modelID2D = ports_calibs[PORT2D]["intrinsic_calibration"].model_id
    intrinsic2D = ports_calibs[PORT2D]["intrinsic_calibration"].parameters
    invModelID2D = ports_calibs[PORT2D]["inverse_intrinsic_calibration"].model_id
    invIntrinsic2D = ports_calibs[PORT2D]["inverse_intrinsic_calibration"].parameters
    extrinsicO2U2D = ports_calibs[PORT2D]["ext_optic_to_user"]
    extrinsic2D = config["ports"][PORT2D]["processing"]["extrinsicHeadToUser"]

    modelID3D = ports_calibs[PORT3D]["intrinsic_calibration"].model_id
    intrinsics3D = ports_calibs[PORT3D]["intrinsic_calibration"].parameters
    invModelID3D = ports_calibs[PORT3D]["inverse_intrinsic_calibration"].model_id
    invIntrinsics3D = ports_calibs[PORT3D]["inverse_intrinsic_calibration"].parameters
    extrinsicO2U3D = ports_calibs[PORT3D]["ext_optic_to_user"]
    extrinsic3D = config["ports"][PORT3D]["processing"]["extrinsicHeadToUser"]

ts = datetime.now().strftime("%d.%m.%Y_%H.%M.%S")

# %%########################################
# Review sample data using matplotlib
############################################

fig = plt.figure(1)
plt.clf()

plt.subplot(2, 2, 1)
plt.title("log(Amplitude) image")
# plt.imshow(np.log(amp + 0.001), cmap="gray", interpolation="none")
plt.imshow(amp, cmap="gray", interpolation="none")
plt.colorbar()

plt.subplot(2, 2, 3)
plt.title("Distance image")
plt.imshow(dis, cmap="jet", interpolation="none")
plt.colorbar()

plt.subplot(1, 2, 2)
plt.title("RGB image")
plt.imshow(jpg, interpolation="none")

# %%#########################################
# Step 1. Transform the 3D pixels to unit
# vectors in the 3D optical frame using the
# intrinsic projection with the 3D intrinsic
# parameters.
#############################################
pixels_3d = dis.shape[::-1]
uvecs_3d_optical_3d = evalIntrinsic(modelID3D, intrinsics3D, *pixels_3d)

pt_cloud_3d_optical = uvecs_3d_optical_3d * dis
fig = plt.figure(1)
plt.clf()
ax = fig.add_subplot(projection="3d")
idx = pt_cloud_3d_optical[2, :] > 0  # plot only valid pixels
plt.plot(pt_cloud_3d_optical[0, idx], pt_cloud_3d_optical[1, idx], -pt_cloud_3d_optical[2, idx], ".", markersize=1)
plt.title("Point cloud without extrinsic parameters (optical frame)")
# %%#########################################
# Step 2. Translate and rotate the 3D unit
# vectors to the camera head frame (a.k.a user
# frame) using the 3D optical to user
# extrinsic parameters
#############################################
# The extrinsic to user parameters received 
# from the camera contain both the optics to
# user values and the user to world values.
# We have to substract the user to world values.
opt_to_user_3d = {}
opt_to_user_3d["rot"] = [
    extrinsicO2U3D.rot_x - extrinsic3D["rotX"],
    extrinsicO2U3D.rot_y - extrinsic3D["rotY"],
    extrinsicO2U3D.rot_z - extrinsic3D["rotZ"],
]
opt_to_user_3d["trans"] = [
    extrinsicO2U3D.trans_x - extrinsic3D["transX"],
    extrinsicO2U3D.trans_y - extrinsic3D["transY"],
    extrinsicO2U3D.trans_z - extrinsic3D["transZ"],
]
# Rotate the unit vectors and apply the translation
uvecs_3d_user = (
    np.array(
        rotMat(
            *np.array(
                (opt_to_user_3d["rot"][0], opt_to_user_3d["rot"][1], opt_to_user_3d["rot"][2])
            )
        ).dot(
            np.stack(
                (
                    uvecs_3d_optical_3d[0].flatten(),
                    uvecs_3d_optical_3d[1].flatten(),
                    uvecs_3d_optical_3d[2].flatten(),
                ),
                axis=0,
            )
        )
    )
    + np.array(
        (opt_to_user_3d["trans"][0], opt_to_user_3d["trans"][1], opt_to_user_3d["trans"][2])
    )[..., np.newaxis]
)

pt_clout_check = uvecs_3d_user * dis.reshape(1, -1)
fig = plt.figure(1)
plt.clf()
ax = fig.add_subplot(projection="3d")
idx = pt_clout_check[2, :] > 0  # plot only valid pixels
plt.plot(pt_clout_check[0, idx], pt_clout_check[1, idx], -pt_clout_check[2, idx], ".", markersize=1)
plt.title("Point cloud without extrinsic parameters (head frame)")

# %%#########################################
# Step3. Translate and rotate the 3D unit
# vectors to the 2D optical frame using the
# 2D optical to user extrinsic parameters
#############################################
opt_to_user_2d = {}
opt_to_user_2d["rot"] = [
    extrinsicO2U2D.rot_x - extrinsic2D["rotX"],
    extrinsicO2U2D.rot_y - extrinsic2D["rotY"],
    extrinsicO2U2D.rot_z - extrinsic2D["rotZ"],
]
opt_to_user_2d["trans"] = [
    extrinsicO2U2D.trans_x - extrinsic2D["transX"],
    extrinsicO2U2D.trans_y - extrinsic2D["transY"],
    extrinsicO2U2D.trans_z - extrinsic2D["transZ"],
]
# Rotate the unit vectors and apply the translation
# Here we use the inverse of the optics to user, since
# we want to go from user to optics
uvecs_3d_optical_2d = (
    np.array(
        rotMat(
            *np.array(
                (opt_to_user_2d["rot"][0], opt_to_user_2d["rot"][1], opt_to_user_2d["rot"][2])
            )
        ).T.dot(
            np.stack(
                (
                    uvecs_3d_user[0].flatten(),
                    uvecs_3d_user[1].flatten(),
                    uvecs_3d_user[2].flatten(),
                ),
                axis=0,
            )
        )
    )
    - np.array(
        (opt_to_user_2d["trans"][0], opt_to_user_2d["trans"][1], opt_to_user_2d["trans"][2])
    )[..., np.newaxis]
)


pt_clout_check = uvecs_3d_optical_2d * dis.reshape(1, -1)
fig = plt.figure(1)
plt.clf()
ax = fig.add_subplot(projection="3d")
idx = pt_clout_check[2, :] > 0  # plot only valid pixels
plt.plot(pt_clout_check[0, idx], pt_clout_check[1, idx], -pt_clout_check[2, idx], ".", markersize=1)
plt.title("Point cloud without extrinsic parameters (2D optical frame)")

# %%#########################################
# Step 4. Project the 3D unit vectors to the
# 2D image plane using the 2D inverse intrinsic
# parameters. This gives us the 2D pixel
# coordinates for each 3D pixel.
#############################################
# We need to get the reverse of the optics to user
# parameters for the 2D camera
user_to_opt_2d = {}
r = rotMatReverse(rotMat(*opt_to_user_2d["rot"]).T)
# t = [-o for o in opt_to_user_2d["trans"]]
t = [-o for o in [extrinsicO2U2D.trans_x, extrinsicO2U2D.trans_y, extrinsicO2U2D.trans_z]]
user_to_opt_2d["rot"] = r
user_to_opt_2d["trans"] = t
corresponding_pixels_2d = inverse_intrinsic_projection(
    camXYZ=uvecs_3d_optical_2d,
    invIC={"modelID": invModelID2D, "modelParameters": invIntrinsic2D},
    camRefToOpticalSystem=user_to_opt_2d,
    binning=0,
)
# Round the pixel coordinates to the nearest integer
corresponding_pixels_2d = np.round(corresponding_pixels_2d).astype(int)

# %%#########################################
# Step 5. Calculate the point cloud
#############################################
point_cloud = uvecs_3d_optical_2d * dis.reshape(1, -1)
# Apply the extrinsic parameters to the point cloud
r = np.array([extrinsic2D["rotX"], extrinsic2D["rotY"], extrinsic2D["rotZ"]])
t = np.array([extrinsic2D["transX"], extrinsic2D["transY"], extrinsic2D["transZ"]])

point_cloud = rotMat(*r).T.dot(point_cloud - np.array(t)[..., np.newaxis])

fig = plt.figure(1)
plt.clf()
ax = fig.add_subplot(projection="3d")
idx = point_cloud[2, :] > 0  # plot only valid pixels
plt.plot(point_cloud[0, idx], point_cloud[1, idx], -point_cloud[2, idx], ".", markersize=1)
plt.title("Point cloud in world frame")

# %%#########################################
# Step 6. Get the color value for each 3D pixel
#############################################
idX = [c for c in corresponding_pixels_2d[0]]
idY = [c for c in corresponding_pixels_2d[1]]

# Get 2D jpg-color for each 3D-pixel
colors = np.zeros((len(idX), 3))  # shape is Nx3 (for open3d)
count=0
for i in range(0, len(colors)):
    if idX[i] >= jpg.shape[0] or idY[i] >= jpg.shape[1] or idX[i] < 0 or idY[i] < 0:
        # print(f"Invalid pixel coordinates: {idX[i]}, {idY[i]}")
        colors[i, 0] = 126
        colors[i, 1] = 126
        colors[i, 2] = 126
        count+=1
    else:
        # print(f"Valid pixel coordinates: {idX[i]}, {idY[i]}")
        colors[i, 0] = jpg[idX[i], idY[i], 0]
        colors[i, 1] = jpg[idX[i], idY[i], 1]
        colors[i, 2] = jpg[idX[i], idY[i], 2]
print(f"Invalid pixels: {count}")


# %%#########################################
# Step 7. Visualize the colored point cloud
#############################################
valid = dis.flatten() > 0.05
print(f"{round(sum(valid)/point_cloud[0].size*100)}% valid pts")
for i, pt_valid in enumerate(valid):
    if not pt_valid:
        point_cloud[0][i] = point_cloud[1][i] = point_cloud[0][i] = 0.0

point_cloud_colored = o3d.geometry.PointCloud()
point_cloud_colored.points = o3d.utility.Vector3dVector(point_cloud.reshape(3, -1)[:, valid].T)
point_cloud_colored.colors = o3d.utility.Vector3dVector(colors[valid] / 255)

if SHOW_OPEN3D:
    o3d.visualization.draw_geometries(
        [point_cloud_colored], window_name=f"Colored point cloud"
    )
