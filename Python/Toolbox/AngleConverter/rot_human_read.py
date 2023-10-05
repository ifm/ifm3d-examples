#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

"""
This module exports functions for converting the euler
calibration angles used in the O3R platform into 
(heading, elevation, bank) angles that are easier
to reason about.
"""
#%%
import numpy as np
import ifm3dpy


def rot_mat(*rot_xyz):
    """
    Creates a rotation matrix from the given euler angles.

    :param rot_xyz: 3 element vector containing rotX, rotY and rotZ in [rad]
    :return: 3x3 rotation matrix R
    """
    R = np.eye(3)
    for i, alpha in enumerate(rot_xyz):
        lr = np.eye(3)
        lr[(i + 1) % 3, (i + 1) % 3] = np.cos(alpha)
        lr[(i + 2) % 3, (i + 2) % 3] = np.cos(alpha)
        lr[(i + 1) % 3, (i + 2) % 3] = -np.sin(alpha)
        lr[(i + 2) % 3, (i + 1) % 3] = np.sin(alpha)
        R = R.dot(lr)
    return R


def rot_mat_reverse(R):
    """
    Calculates euler angles from a rotation matrix.
    This is the inverse of the rot_mat() function.

    :param R: 3x3 rotation matrix
    :return: rotX, rotY, rotZ in [rad]
    """
    alpha = np.arctan2(R[1, 2], R[2, 2])
    c2 = np.sqrt(R[0, 0] ** 2 + R[0, 1] ** 2)
    beta = np.arctan2(-R[0, 2], c2)
    s1 = np.sin(alpha)
    c1 = np.cos(alpha)
    gamma = np.arctan2(s1 * R[2, 0] - c1 * R[1, 0], c1 * R[1, 1] - s1 * R[2, 1])
    rotX, rotY, rotZ = -alpha, -beta, -gamma
    if rotX < -np.pi / 2 or rotX > np.pi / 2:
        if rotX < 0:
            rotX += np.pi
        else:
            rotX -= np.pi
        rotY = np.pi - rotY
        if rotY < -np.pi:
            rotY += 2 * np.pi
        if rotY > np.pi:
            rotY -= 2 * np.pi
        rotZ = rotZ + np.pi
        if rotZ > np.pi:
            rotZ -= 2 * np.pi
    return rotX, rotY, rotZ


# It's easy to reason about rotations relative to a "default head position".
# This is camera facing +x, label facing +z in the ODS coordinate system,
# which corresponds to typical robot coordinate system.
DEFAULT_O3R_HEAD_ROTATION_FOR_ODS = rot_mat(0, np.pi / 2, -np.pi / 2)
# Each intrinsic rotation that is applied requires
# a conventional direction designated by "SIGNS".
SIGNS = (1, 1, 1)


def human_readable_to_O3R_angles(*heading_elevation_bank) -> tuple:
    """Convert (H, E, B) angles to Euler angles in the O3R coordinate system.

    :returns tuple: rot_xyz the three rotations in the O3R coordinate system
    """
    rot = DEFAULT_O3R_HEAD_ROTATION_FOR_ODS
    for angle, axis, sign in zip(
        heading_elevation_bank, np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]]), SIGNS
    ):
        rot = rot.dot(rot_mat(*(sign * axis * angle * np.pi / 180)))
    rot_xyz = rot_mat_reverse(rot)
    return rot_xyz


def O3R_angles_to_human_readable(*rot_xyz) -> tuple:
    """Convert O3R Euler angles to "human-readable" (H, E, B) angles.

    :param *rot_xyz (float): o3r_head_rotations
    :returns tuple: heading, elevation, and bank angles
                    relative to DEFAULT_O3R_HEAD_ROTATION_FOR_ODS
    """
    rot = rot_mat(*rot_xyz)  # the rotated direction of camera view
    fov_uv = np.array(
        np.dot(rot, (0, 0, 1))
    )  # the rotated direction of camera view on x-y plane
    heading_vector = fov_uv[:2]  # find heading and elevation
    if not np.any(
        heading_vector
    ):  # Avoid singularities where camera is pointing + or - z
        heading = 0
        elevation = SIGNS[1] * 90 * np.sign(fov_uv[2])
    else:
        heading = SIGNS[0] * (np.arctan2(*heading_vector) * 180 / np.pi - 90)
        elevation = (
            SIGNS[1] * np.arctan2(fov_uv[2], np.linalg.norm(fov_uv[:2])) * 180 / np.pi
        )
    # Find bank angle
    heading_elevation = DEFAULT_O3R_HEAD_ROTATION_FOR_ODS
    for angle, axis, sign in zip(
        (heading, elevation), np.array([[0, 1, 0], [1, 0, 0]]), SIGNS[:2]
    ):
        heading_elevation = heading_elevation.dot(
            rot_mat(*(sign * axis * angle * np.pi / 180))
        )
    x_ax = heading_elevation.dot((1, 0, 0))
    y_ax = heading_elevation.dot((0, 1, 0))
    x_ax_with_bank_angle = rot.dot((1, 0, 0))
    bank = (
        SIGNS[2]
        * np.arctan2(
            np.dot(y_ax, x_ax_with_bank_angle), np.dot(x_ax, x_ax_with_bank_angle)
        )
        * 180
        / np.pi
    )

    return heading, elevation, bank


#%%


# Some boilerplate for getting and setting rotations of cameras
# so that we can visualize the effect of changing the human-readable angles
def set_rotation(o3r: ifm3dpy.O3R, port_ns: list, rot: tuple, verbose=False):
    for port_n in port_ns:
        extrinsic_cal_name = "extrinsicHeadToUser"
        if port_n == 6:
            extrinsic_cal_name = "extrinsicVPUToUser"
        if verbose:
            print(f"euler angles: {rot}")
        ext_dict = o3r.get()["ports"][f"port{port_n}"]["processing"][extrinsic_cal_name]
        ext_dict.update({k: v for k, v in zip(["rotX", "rotY", "rotZ"], rot)})
        config = {
            "ports": {f"port{port_n}": {"processing": {extrinsic_cal_name: ext_dict}}}
        }
        o3r.set(config)


heading, elevation, bank = (0, 0, 0)

print("Before transformation...")
print("heading=", round(heading, 2))
print("elevation=", round(elevation, 2))
print("bank=", round(bank, 2))
rot_xyz = human_readable_to_O3R_angles(heading, elevation, bank)
print("o3r calibration angles:", rot_xyz)
set_rotation(ifm3dpy.O3R(), [2], list(rot_xyz))
heading, elevation, bank = O3R_angles_to_human_readable(*rot_xyz)
print("\nAfter transformation...")
print("heading=", round(heading, 2))
print("elevation=", round(elevation, 2))
print("bank=", round(bank, 2))
# %%
