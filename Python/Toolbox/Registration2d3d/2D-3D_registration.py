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

#%%
from datetime import datetime
from pathlib import Path
import os
import cv2
import matplotlib.pyplot as plt
import open3d as o3d
import numpy as np

from transforms import (
    intrinsic_projection,
    inverse_intrinsic_projection,
    translate,
    rotate_xyz,
    rectify,
    rotMat,
)


#%%##########################################
# Define camera ports and VPU IP address
# CONFIGURE FOR YOUR SETUP
############################################
IP_ADDR = "192.168.0.69"  # This is the default address
PORT2D = "port1"
PORT3D = "port3"

############################################
# Read data from file or use live data
############################################
USE_RECORDED_DATA = False
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


#%%#########################################
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

    current_dir = Path(__file__).parent.resolve()

    # Unpack all data required to 2d3d registration
    hf1 = h5py.File(str(current_dir / FILE_NAME), "r")

    config = json.loads(hf1["streams"]["o3r_json"]["data"][0].tobytes())
    check_heads_requirements(config=config)

    # If the recording contains data from more than one head,
    # pick the proper stream (it might be "o3r_rgb_1" and "o3r_tof_1")
    rgb = hf1["streams"]["o3r_rgb_0"]
    tof = hf1["streams"]["o3r_tof_0"]

    jpg = rgb[0]["jpeg"]
    jpg = cv2.imdecode(jpg, cv2.IMREAD_UNCHANGED)
    jpg = cv2.cvtColor(jpg, cv2.COLOR_BGR2RGB)
    modelID2D = rgb[0]["intrinsicCalibModelID"]
    intrinsic2D = rgb[0]["intrinsicCalibModelParameters"]
    invIntrinsic2D = rgb[0]["invIntrinsicCalibModelParameters"]
    extrinsic2D = ExtrinsicOpticToUser()
    extrinsic2D.trans_x = rgb[0]["extrinsicOpticToUserTrans"][0]
    extrinsic2D.trans_y = rgb[0]["extrinsicOpticToUserTrans"][1]
    extrinsic2D.trans_z = rgb[0]["extrinsicOpticToUserTrans"][2]
    extrinsic2D.rot_x = rgb[0]["extrinsicOpticToUserRot"][0]
    extrinsic2D.rot_y = rgb[0]["extrinsicOpticToUserRot"][1]
    extrinsic2D.rot_z = rgb[0]["extrinsicOpticToUserRot"][2]

    dis = tof[0]["distance"]
    amp = tof[0]["amplitude"]
    modelID3D = tof[0]["intrinsicCalibModelID"]
    intrinsics3D = tof[0]["intrinsicCalibModelParameters"]
    inv_intrinsics3D = tof[0]["invIntrinsicCalibModelParameters"]
    extrinsic3D = ExtrinsicOpticToUser()
    extrinsic3D.trans_x = tof[0]["extrinsicOpticToUserTrans"][0]
    extrinsic3D.trans_y = tof[0]["extrinsicOpticToUserTrans"][1]
    extrinsic3D.trans_z = tof[0]["extrinsicOpticToUserTrans"][2]
    extrinsic3D.rot_x = tof[0]["extrinsicOpticToUserRot"][0]
    extrinsic3D.rot_y = tof[0]["extrinsicOpticToUserRot"][1]
    extrinsic3D.rot_z = tof[0]["extrinsicOpticToUserRot"][2]
    hf1.close()

############################################
# Live data from connected o3r system
############################################
else:
    from ifm3dpy.device import O3R

    from collect_calibrations import PortCalibrationCollector
    from loop_to_collect_frame import FrameCollector

    o3r = O3R(IP_ADDR)
    config = o3r.get()

    camera_ports = [PORT2D, PORT3D]
    check_heads_requirements(config=config)

    ############################################
    # Collect port info and retrieve and unpack
    # the calibration data for each requested port.
    ############################################
    ports_info = {
        camera_ports[i]: o3r.port(camera_ports[i]) for i in range(0, len(camera_ports))
    }
    ports_calibs = {
        ports_info[port_n]
        .port: PortCalibrationCollector(o3r, ports_info[port_n])
        .collect()
        for port_n in camera_ports
    }

    #%%##########################################
    # Record sample frames for registration
    #############################################
    frame_collector = FrameCollector(o3r, ports=camera_ports)
    frame_collector.loop(timeout=10000)

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
    invIntrinsic2D = ports_calibs[PORT2D]["inverse_intrinsic_calibration"].parameters
    extrinsic2D = ports_calibs[PORT2D]["ext_optic_to_user"]

    modelID3D = ports_calibs[PORT3D]["intrinsic_calibration"].model_id
    intrinsics3D = ports_calibs[PORT3D]["intrinsic_calibration"].parameters
    inv_intrinsics3D = ports_calibs[PORT3D]["inverse_intrinsic_calibration"].parameters
    extrinsic3D = ports_calibs[PORT3D]["ext_optic_to_user"]

ts = datetime.now().strftime("%d.%m.%Y_%H.%M.%S")

#%%########################################
# Review sample data using matplotlib
############################################

fig = plt.figure(1)
plt.clf()

plt.subplot(2, 2, 1)
plt.title("log(Amplitude) image")
plt.imshow(np.log10(amp + 0.001), cmap="gray", interpolation="none")
plt.colorbar()

plt.subplot(2, 2, 3)
plt.title("Distance image")
plt.imshow(dis, cmap="jet", interpolation="none")
plt.colorbar()

plt.subplot(1, 2, 2)
plt.title("RGB image")
plt.imshow(jpg, interpolation="none")

#%%#########################################
# Point cloud calculations
############################################

# calculate 3D unit vectors corresponding to each pixel of depth camera
ux, uy, uz = intrinsic_projection(modelID3D, intrinsics3D, *dis.shape[::-1])

# multiply unit vectors by depth of corresponding pixel
x = (ux * dis).flatten()
y = (uy * dis).flatten()
z = (uz * dis).flatten()
valid = dis.flatten() > 0.05
print(f"{round(sum(valid)/x.size*100)}% valid pts")
for i, pt_valid in enumerate(valid):
    if not pt_valid:
        x[i] = y[i] = z[i] = 0.0

# Restructure point cloud as sequence of points
pcd_o3 = np.stack((x, y, z), axis=0)

# Transform from optical coordinate system
# to user coordinate system
pcd_u = translate(
    rotate_xyz(pcd_o3, extrinsic3D.rot_x, extrinsic3D.rot_y, extrinsic3D.rot_z),
    extrinsic3D.trans_x,
    extrinsic3D.trans_y,
    extrinsic3D.trans_z,
)
#%%#########################################
# Visualize point cloud using matplotlib
############################################
fig = plt.figure(1)
plt.clf()
ax = fig.add_subplot(projection="3d")
idx = pcd_o3[2, :] > 0  # plot only valid pixels
plt.plot(pcd_o3[0, idx], pcd_o3[1, idx], -pcd_o3[2, idx], ".", markersize=1)
plt.title("Point cloud")

# Visualize 3D-Pointcloud colored with log(amplitude)
# The amplitude image is good for visualizing the reflectivity of various materials
pointcloud = o3d.geometry.PointCloud()
pointcloud.points = o3d.utility.Vector3dVector(pcd_o3[:, valid].T)
colors = np.log10(amp + 0.001).flatten()
colors = (colors - np.min(colors)) / (np.max(colors) - np.min(colors))
colors = np.stack((colors, colors, colors), axis=1)
pointcloud.colors = o3d.utility.Vector3dVector(colors[valid])

# render 3D pointcloud
if SHOW_OPEN3D:
    o3d.visualization.draw_geometries(
        [pointcloud], window_name="Amplitude - Head coordinate system"
    )

#%%#########################################
# Do rectification of 3D amplitude image using intrinsic parameters
############################################
fig = plt.figure(1)
plt.clf()
im_rect = rectify(inv_intrinsics3D, modelID3D, np.log10(amp + 0.001))

plt.subplot(1, 2, 1)
plt.imshow(np.log10(amp + 0.001))
plt.title("log(Amplitude)")
plt.subplot(1, 2, 2)
plt.imshow(im_rect)
plt.title("Rectified log(Amplitude)")
plt.show()

#%%#########################################
# Do rectification of 2D image using intrinsic parameters
############################################
fig = plt.figure(1)
plt.clf()

im_rect = rectify(invIntrinsic2D, modelID2D, jpg)

plt.subplot(1, 2, 1)
plt.imshow(jpg)
plt.title("Raw Color Im.")
plt.subplot(1, 2, 2)
plt.imshow(im_rect)
plt.title("Rectified Color Im.")
plt.show()

#%%#########################################
# Color each 3D point with it's corresponding 2D pixel
############################################
# convert to points in optics space
# reverse internalTransRot
r = np.array([extrinsic2D.rot_x, extrinsic2D.rot_y, extrinsic2D.rot_z])
t = np.array([extrinsic2D.trans_x, extrinsic2D.trans_y, extrinsic2D.trans_z])

# pcd = rotate_zyx(translate(pcd,*t),*r)
pcd_o2 = rotMat(r).T.dot(pcd_u - np.array(t)[..., np.newaxis])

# Calculate 2D pixel coordinates for each 3D pixel
pixels = np.round(inverse_intrinsic_projection(pcd_o2, invIntrinsic2D, modelID2D))

# Get 2D jpg-color for each 3D-pixel
colors = np.zeros((len(pixels[0]), 3))  # shape is Nx3 (for open3d)
for i in range(len(colors)):
    idxX = int(pixels[1][i])
    idxY = int(pixels[0][i])
    # Ignore invalid values
    if idxY > 1279 or idxX > 799 or idxY < 0 or idxX < 0:
        colors[i, 0] = 126
        colors[i, 1] = 126
        colors[i, 2] = 126
    else:
        colors[i, 0] = jpg[idxX, idxY, 0]
        colors[i, 1] = jpg[idxX, idxY, 1]
        colors[i, 2] = jpg[idxX, idxY, 2]


# save results for later display using open3d
results_dir = Path(__file__).parent / "results"
if not results_dir.exists():
    os.mkdir(results_dir)
cam_sn = config["ports"][f"{PORT3D}"]["info"]["serialNumber"]

colored_pointcloud_valid = o3d.geometry.PointCloud()
colored_pointcloud_valid.points = o3d.utility.Vector3dVector(pcd_u[:, valid].T)
colored_pointcloud_valid.colors = o3d.utility.Vector3dVector(colors[valid] / 255)
dst_valid = str(results_dir / f"{ts}_{cam_sn}_{dis.shape[1]}x{dis.shape[0]}_valid_.pcd")
o3d.io.write_point_cloud(dst_valid, colored_pointcloud_valid, print_progress=True)
colored_pointcloud_all = o3d.geometry.PointCloud()
colored_pointcloud_all.points = o3d.utility.Vector3dVector(pcd_u.T)
colored_pointcloud_all.colors = o3d.utility.Vector3dVector(colors / 255)
dst_all = str(results_dir / f"{ts}_{cam_sn}_{dis.shape[1]}x{dis.shape[0]}_all_.pcd")
o3d.io.write_point_cloud(dst_all, colored_pointcloud_all, print_progress=True)

#%%#########################################
# review results
############################################
colored_pointcloud_valid = o3d.io.read_point_cloud(dst_valid)
print(colored_pointcloud_valid)
print(np.asarray(colored_pointcloud_valid.points))
if SHOW_OPEN3D:
    o3d.visualization.draw_geometries(
        [colored_pointcloud_valid], window_name=f"Colored points - {cam_sn} "
    )

#%%##########################################
# review samples or other results...
############################################
src_dir = Path(__file__).parent / "samples"
src = results_dir / f"{ts}_{cam_sn}_{dis.shape[1]}x{dis.shape[0]}_all_.pcd"
src = results_dir / f"{ts}_{cam_sn}_{dis.shape[1]}x{dis.shape[0]}_valid_.pcd"
pcd = o3d.io.read_point_cloud(str(src))
print(pcd)
print(np.asarray(pcd.points))
if SHOW_OPEN3D:
    o3d.visualization.draw_geometries(
        [pcd], window_name="Colored points - Head coordinate system"
    )
