# -*- coding: utf-8 -*-
#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This module provides an example on how to register the 2D and 3D
# images of a single camera head to obtain a colored point cloud.
# The example can be run using live data obtained from the camera or
# a recording.

# To understand all the steps involved in the registration, we
# recommend to go through the colorize_point_cloud() function which shows
# the step by step process along with visualization of the
# point cloud after each transformation.

# The other functions in this module are helper functions.

# %%
import logging

import cv2
import matplotlib.pyplot as plt
import numpy as np
import open3d as o3d
from o3r_algo_utilities.calib.point_correspondences import inverse_intrinsic_projection
from o3r_algo_utilities.o3r_uncompress_di import evalIntrinsic
from o3r_algo_utilities.rotmat import rotMat

logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)


# %%#########################################
# Defining helper functions
#############################################
def check_heads_requirements(config: dict, port2d: str, port3d: str):
    """Verifies that the provided ports can be used for registration.

    :param config: the full json configuration of the device being used.
    :raises ValueError: if the provided ports fo not belong to the same camera head.
    :raises ValueError: if the provided ports are calibrated with different values.
    :raises ValueError: if the provided ports have the same type.
    """
    # Check that ports from the same camera head are provided
    if (
        config["ports"][port2d]["info"]["serialNumber"]
        != config["ports"][port3d]["info"]["serialNumber"]
    ):
        raise ValueError("2D and 3D ports must belong to the same camera head.")

    if (
        config["ports"][port2d]["processing"]["extrinsicHeadToUser"]
        != config["ports"][port3d]["processing"]["extrinsicHeadToUser"]
    ):
        raise ValueError(" 2D and 3D ports should have the same extrinsic calibration")

    if (
        config["ports"][port2d]["info"]["features"]["type"]
        == config["ports"][port3d]["info"]["features"]["type"]
    ):
        raise ValueError("The ports must have different types.")


def collect_data_from_live(port2d: str, port3d: str, ip: str):
    from ifm3dpy.deserialize import RGBInfoV1, TOFInfoV4
    from ifm3dpy.device import O3R
    from ifm3dpy.framegrabber import FrameGrabber, buffer_id

    # Collect a 2D and a 3D frame to use for registration
    o3r = O3R(ip)

    # Verify that the port provided correspond to the same camera head
    # and are properly calibrated
    config = o3r.get()
    try:
        check_heads_requirements(config=config, port2d=port2d, port3d=port3d)
    except ValueError as e:
        raise ValueError(e) from e
    fg_2d = FrameGrabber(o3r, o3r.port(port2d).pcic_port)
    fg_3d = FrameGrabber(o3r, o3r.port(port3d).pcic_port)
    fg_2d.start([buffer_id.JPEG_IMAGE, buffer_id.RGB_INFO])
    fg_3d.start(
        [buffer_id.RADIAL_DISTANCE_IMAGE, buffer_id.AMPLITUDE_IMAGE, buffer_id.TOF_INFO]
    )
    [ok_2d, frame_2d] = fg_2d.wait_for_frame().wait_for(1000)
    [ok_3d, frame_3d] = fg_3d.wait_for_frame().wait_for(1000)
    if not ok_2d or not ok_3d:
        raise TimeoutError("No frame was collected.")

    # Unpack all data relevant to 2d3d registration
    # Image data (RGB, distance, and amplitude)
    jpg = cv2.imdecode(frame_2d.get_buffer(buffer_id.JPEG_IMAGE), cv2.IMREAD_UNCHANGED)
    jpg = cv2.cvtColor(jpg, cv2.COLOR_BGR2RGB)
    dis = frame_3d.get_buffer(buffer_id.RADIAL_DISTANCE_IMAGE)
    amp = frame_3d.get_buffer(buffer_id.NORM_AMPLITUDE_IMAGE)

    # Calibration data
    rgb_info = RGBInfoV1().deserialize(frame_2d.get_buffer(buffer_id.RGB_INFO))
    invModelID2D = rgb_info.inverse_intrinsic_calibration.model_id
    invIntrinsic2D = rgb_info.inverse_intrinsic_calibration.parameters
    extrinsicO2U2D = rgb_info.extrinsic_optic_to_user

    tof_info = TOFInfoV4().deserialize(frame_3d.get_buffer(buffer_id.TOF_INFO))
    modelID3D = tof_info.intrinsic_calibration.model_id
    intrinsics3D = tof_info.intrinsic_calibration.parameters
    extrinsicO2U3D = tof_info.extrinsic_optic_to_user

    return (
        jpg,
        dis,
        amp,
        invModelID2D,
        invIntrinsic2D,
        extrinsicO2U2D,
        modelID3D,
        intrinsics3D,
        extrinsicO2U3D,
    )


def collect_data_from_rec(file_path: str):
    import json

    import h5py

    class ExtrinsicOpticToUser:
        def __init__(self) -> None:
            self.trans_x = 0.0
            self.trans_y = 0.0
            self.trans_z = 0.0
            self.rot_x = 0.0
            self.rot_y = 0.0
            self.rot_z = 0.0

    # Unpack all data required to 2d3d registration
    hf1 = h5py.File(file_path, "r")

    config = json.loads(hf1["streams"]["o3r_json"]["data"][0].tobytes())
    port2d = None
    port3d = None
    # Pick the first available 2D and 3D heads
    for port in config["ports"]:
        if config["ports"][port]["info"]["features"]["type"] == "2D":
            if port2d is None:
                port2d = port
        elif config["ports"][port]["info"]["features"]["type"] == "3D":
            if port3d is None:
                port3d = port

    check_heads_requirements(config=config, port2d=port2d, port3d=port3d)

    # If the recording contains data from more than one head,
    # pick the proper stream (it might be "o3r_rgb_1" and "o3r_tof_1")
    try:
        rgb = hf1["streams"]["o3r_rgb_0"]
        tof = hf1["streams"]["o3r_tof_0"]
    except KeyError as e:
        msg = """The recording does not contain the required streams.
            The streams are named after the camera index, not the port number.
            The first TOF camera stream is o3r_rgb_0, the second TOF camera is o3r_rgb_1, and so on.
            The same applied to the RGB camera stream."""
        raise ValueError(msg) from e

    jpg = rgb[0]["jpeg"]
    jpg = cv2.imdecode(jpg, cv2.IMREAD_UNCHANGED)
    jpg = cv2.cvtColor(jpg, cv2.COLOR_BGR2RGB)
    invModelID2D = rgb[0]["invIntrinsicCalibModelID"]
    invIntrinsic2D = rgb[0]["invIntrinsicCalibModelParameters"]
    extrinsicO2U2D = ExtrinsicOpticToUser()
    extrinsicO2U2D.trans_x = rgb[0]["extrinsicOpticToUserTrans"][0]
    extrinsicO2U2D.trans_y = rgb[0]["extrinsicOpticToUserTrans"][1]
    extrinsicO2U2D.trans_z = rgb[0]["extrinsicOpticToUserTrans"][2]
    extrinsicO2U2D.rot_x = rgb[0]["extrinsicOpticToUserRot"][0]
    extrinsicO2U2D.rot_y = rgb[0]["extrinsicOpticToUserRot"][1]
    extrinsicO2U2D.rot_z = rgb[0]["extrinsicOpticToUserRot"][2]

    dis = tof[0]["distance"]
    amp = tof[0]["amplitude"]
    modelID3D = tof[0]["intrinsicCalibModelID"]
    intrinsics3D = tof[0]["intrinsicCalibModelParameters"]
    extrinsicO2U3D = ExtrinsicOpticToUser()
    extrinsicO2U3D.trans_x = tof[0]["extrinsicOpticToUserTrans"][0]
    extrinsicO2U3D.trans_y = tof[0]["extrinsicOpticToUserTrans"][1]
    extrinsicO2U3D.trans_z = tof[0]["extrinsicOpticToUserTrans"][2]
    extrinsicO2U3D.rot_x = tof[0]["extrinsicOpticToUserRot"][0]
    extrinsicO2U3D.rot_y = tof[0]["extrinsicOpticToUserRot"][1]
    extrinsicO2U3D.rot_z = tof[0]["extrinsicOpticToUserRot"][2]
    hf1.close()
    return (
        jpg,
        dis,
        amp,
        invModelID2D,
        invIntrinsic2D,
        extrinsicO2U2D,
        modelID3D,
        intrinsics3D,
        extrinsicO2U3D,
    )


def plot_point_cloud(pt_cloud, title):
    #############################################
    # Some boilerplate for plotting the point clouds
    #############################################
    fig = plt.figure(1)
    plt.clf()
    ax = fig.add_subplot(projection="3d")
    plt.plot(*pt_cloud, ".", markersize=1)
    plt.xlabel("X")
    plt.ylabel("Y")
    ax.set_zlabel("Z")
    plt.title(title)
    plt.show()


def colorize_point_cloud(
    jpg,
    dis,
    amp,
    invModelID2D,
    invIntrinsic2D,
    extrinsicO2U2D,
    modelID3D,
    intrinsics3D,
    extrinsicO2U3D,
):
    #############################################
    # Step 1. Calculate the unit vectors for the
    # 3D camera in the 3D optical coordinate system
    # using the intrinsic projection parameters.
    #############################################
    height_width_3d = dis.shape[::-1]
    unit_vectors_3d_in_3d_opt = evalIntrinsic(modelID3D, intrinsics3D, *height_width_3d)

    #############################################
    # Step 2. Calculate the point cloud by multiplying
    # the unit vectors with the distance values.
    # The point cloud is in the 3D optical coordinate system.
    #############################################
    pt_cloud_in_3d_opt = unit_vectors_3d_in_3d_opt * dis

    # Flatten the point cloud
    pt_cloud_in_3d_opt = pt_cloud_in_3d_opt.reshape(3, -1)
    valid_points_indices = pt_cloud_in_3d_opt[2] > 0

    # Log the number of valid points and plot the point cloud
    print(f"shape of point cloud: {pt_cloud_in_3d_opt.shape}")
    plot_point_cloud(
        pt_cloud_in_3d_opt[:, valid_points_indices],
        "Point cloud without extrinsic parameters (3D optical CoSy)",
    )
    #############################################
    # Step 3. Transform the point cloud to the
    # user coordinate system using the extrinsic
    # calibration parameters.
    #############################################
    opt_to_user_3d = {
        "rot": [
            extrinsicO2U3D.rot_x,
            extrinsicO2U3D.rot_y,
            extrinsicO2U3D.rot_z,
        ],
        "trans": [
            extrinsicO2U3D.trans_x,
            extrinsicO2U3D.trans_y,
            extrinsicO2U3D.trans_z,
        ],
    }

    pt_cloud_in_user = (
        np.array(
            rotMat(
                *np.array(
                    (
                        opt_to_user_3d["rot"][0],
                        opt_to_user_3d["rot"][1],
                        opt_to_user_3d["rot"][2],
                    )
                )
            ).dot(pt_cloud_in_3d_opt)
        )
        + np.array(opt_to_user_3d["trans"])[..., np.newaxis]
    )

    # Log the shape of the point cloud and plot it
    print(f"shape of point cloud: {pt_cloud_in_user.shape}")
    plot_point_cloud(
        pt_cloud_in_user[:, valid_points_indices], "Point cloud (User CoSy)"
    )
    #############################################
    # Step 4. Transform the point cloud to the 2D
    # optical coordinate system.
    #############################################
    opt_to_user_2d = {}
    opt_to_user_2d["rot"] = [
        extrinsicO2U2D.rot_x,
        extrinsicO2U2D.rot_y,
        extrinsicO2U2D.rot_z,
    ]
    opt_to_user_2d["trans"] = [
        extrinsicO2U2D.trans_x,
        extrinsicO2U2D.trans_y,
        extrinsicO2U2D.trans_z,
    ]

    pt_cloud_in_2d_opt = np.array(
        rotMat(
            *np.array(
                (
                    opt_to_user_2d["rot"][0],
                    opt_to_user_2d["rot"][1],
                    opt_to_user_2d["rot"][2],
                )
            )
        ).T.dot(pt_cloud_in_user - np.array(opt_to_user_2d["trans"])[..., np.newaxis])
    )

    # Log the shape of the point cloud and plot it
    print(f"shape of point cloud: {pt_cloud_in_2d_opt.shape}")
    plot_point_cloud(
        pt_cloud_in_2d_opt[:, valid_points_indices],
        "Point cloud in 2D optical frame (2D CoSy)",
    )

    #############################################
    # Step 5. Project the 3D point cloud to the
    # 2D image plane using the 2D inverse intrinsic
    # parameters. This gives us the 2D pixel
    # coordinates for each 3D pixel.
    #############################################

    corresponding_pixels_2d = inverse_intrinsic_projection(
        camXYZ=pt_cloud_in_2d_opt,
        invIC={"modelID": invModelID2D, "modelParameters": invIntrinsic2D},
        camRefToOpticalSystem={"rot": (0, 0, 0), "trans": (0, 0, 0)},
        binning=0,
    )
    # Round the pixel coordinates to the nearest integer
    corresponding_pixels_2d = np.round(corresponding_pixels_2d).astype(int)

    #############################################
    # Step 6. Get the color value for each 3D pixel
    #############################################
    idX = corresponding_pixels_2d[1]
    idY = corresponding_pixels_2d[0]

    # Get 2D jpg-color for each 3D-pixel
    colors = np.zeros((len(idX), 3))  # shape is Nx3 (for open3d)
    count = 0
    for i in range(0, len(colors)):
        if idX[i] >= jpg.shape[0] or idY[i] >= jpg.shape[1] or idX[i] < 0 or idY[i] < 0:
            colors[i, 0] = 126
            colors[i, 1] = 126
            colors[i, 2] = 126
            count += 1
        else:
            colors[i, 0] = jpg[idX[i], idY[i], 0]
            colors[i, 1] = jpg[idX[i], idY[i], 1]
            colors[i, 2] = jpg[idX[i], idY[i], 2]

    print(f"Invalid pixels (usually objects too far or too dim): {count}")

    return pt_cloud_in_user, colors


# %%#########################################
# Main function which shows the step by step
# registration of the 2D and 3D images
#############################################
def main(ip, port2d, port3d, use_recorded_data, file_path, show_open3d):
    ############################################
    # Load recorded data in h5 format. We expect
    # data to be in the format provided by the
    # Vision Assistant.
    ############################################
    if use_recorded_data:
        (
            jpg,
            dis,
            amp,
            invModelID2D,
            invIntrinsic2D,
            extrinsicO2U2D,
            modelID3D,
            intrinsics3D,
            extrinsicO2U3D,
        ) = collect_data_from_rec(file_path=file_path)

    ############################################
    # Alternatively, collect live data from the camera
    ############################################
    else:
        (
            jpg,
            dis,
            amp,
            invModelID2D,
            invIntrinsic2D,
            extrinsicO2U2D,
            modelID3D,
            intrinsics3D,
            extrinsicO2U3D,
        ) = collect_data_from_live(port2d=port2d, port3d=port3d, ip=ip)

    ############################################
    # Review sample data using matplotlib
    ############################################

    plt.figure(1)
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
    plt.show()

    ############################################
    # Colorize the point cloud
    ############################################
    pt_cloud_in_user, colors = colorize_point_cloud(
        jpg,
        dis,
        amp,
        invModelID2D,
        invIntrinsic2D,
        extrinsicO2U2D,
        modelID3D,
        intrinsics3D,
        extrinsicO2U3D,
    )
    ############################################
    # Visualize the colored point cloud
    #############################################
    valid = dis.flatten() > 0.05
    print(f"{round(sum(valid)/pt_cloud_in_user[0].size*100)}% valid pts")
    for i, pt_valid in enumerate(valid):
        if not pt_valid:
            pt_cloud_in_user[0][i] = pt_cloud_in_user[1][i] = pt_cloud_in_user[0][
                i
            ] = 0.0

    point_cloud_colored = o3d.geometry.PointCloud()
    point_cloud_colored.points = o3d.utility.Vector3dVector(
        pt_cloud_in_user.reshape(3, -1)[:, valid].T
    )
    point_cloud_colored.colors = o3d.utility.Vector3dVector(colors[valid] / 255)

    if show_open3d:
        o3d.visualization.draw_geometries(
            [point_cloud_colored], window_name="Colored point cloud"
        )

    # %%


if __name__ == "__main__":
    ############################################
    # Chose if you want to user recorded data or
    # live data from the camera
    ############################################
    # If using recorded data, the file path provided in the config.py file will be used.
    # If multiple frames are available in the file,
    # then the first frame will be used.
    USE_RECORDED_DATA = False

    ############################################
    # Import the device configuration from the config file
    ############################################
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
        PORT2D = config.PORT_2D
        PORT3D = config.PORT_3D
        if USE_RECORDED_DATA:
            FILE_PATH = config.SAMPLE_DATA

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        PORT2D = "port0"
        PORT3D = "port2"
        if USE_RECORDED_DATA:
            FILE_PATH = "./test_rec.h5"

    # Show 3D cloud or not.
    SHOW_OPEN3D = True
    if not USE_RECORDED_DATA:
        FILE_PATH = ""
    main(
        ip=IP,
        port2d=PORT2D,
        port3d=PORT3D,
        use_recorded_data=USE_RECORDED_DATA,
        file_path=FILE_PATH,
        show_open3d=SHOW_OPEN3D,
    )
