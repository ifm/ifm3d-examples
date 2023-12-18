#!/usr/bin/env python

#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################


import argparse
from pathlib import Path

import numpy as np
import json
import h5py

import matplotlib.pyplot as plt
import logging


logger = logging.getLogger(__name__)


def intrinsic_projection(intrinsicModelID, intrinsicModelParameters, width, height):
    """Evaluate intrinsic calibration model parameter and return unit vectors in the optical reference system

    Args:
        intrinsicModelID (int): intrinsic model id
        intrinsicModelParameters (numpy array): intrinsics model parameter as returned from the camera (as part of the image chunk)
        width (int): image width
        height (int): image height

    Raises:
        RuntimeError: raises Runtime error if modelID doesn't exist

    Returns:
        tuple: direction vector in the optical reference system
    """

    if intrinsicModelID == 0:  # Bouguet model
        fx, fy, mx, my, alpha, k1, k2, k3, k4, k5 = intrinsicModelParameters[:10]
        iy, ix = np.indices((height, width))
        cx = (ix + 0.5 - mx) / fx
        cy = (iy + 0.5 - my) / fy
        cx -= alpha * cy
        r2 = cx**2 + cy**2
        fradial = 1 + r2 * (k1 + r2 * (k2 + r2 * k5))
        h = 2 * cx * cy
        tx = k3 * h + k4 * (r2 + 2 * cx**2)
        ty = k3 * (r2 + 2 * cy**2) + k4 * h
        dx = fradial * cx + tx
        dy = fradial * cy + ty
        fnorm = 1 / np.sqrt(dx**2 + dy**2 + 1)
        vx = fnorm * dx
        vy = fnorm * dy
        vz = fnorm
        return vx, vy, vz
    elif intrinsicModelID == 2:  # fish eye model
        fx, fy, mx, my, alpha, k1, k2, k3, k4, theta_max = intrinsicModelParameters[:10]
        iy, ix = np.indices((height, width))
        cx = (ix + 0.5 - mx) / fx
        cy = (iy + 0.5 - my) / fy
        cx -= alpha * cy
        theta_s = np.sqrt(cx**2 + cy**2)
        phi_s = np.minimum(theta_s, theta_max)
        p_radial = 1 + phi_s**2 * (
            k1 + phi_s**2 * (k2 + phi_s**2 * (k3 + phi_s**2 * k4))
        )
        theta = theta_s * p_radial
        theta = np.clip(
            theta, 0, np.pi
        )  # -> avoid surprises at image corners of extreme fisheyes
        vx = np.choose((theta_s > 0), (0, (cx / theta_s) * np.sin(theta)))
        vy = np.choose((theta_s > 0), (0, (cy / theta_s) * np.sin(theta)))
        vz = np.cos(theta)
        return vx, vy, vz
    else:
        raise RuntimeError("Unknown model %d" % intrinsicModelID)


def rotMat(r, order=(0, 1, 2)):
    R = np.eye(3)
    for i in order:
        lr = np.eye(3)
        lr[(i + 1) % 3, (i + 1) % 3] = np.cos(r[i])
        lr[(i + 2) % 3, (i + 2) % 3] = np.cos(r[i])
        lr[(i + 1) % 3, (i + 2) % 3] = -np.sin(r[i])
        lr[(i + 2) % 3, (i + 1) % 3] = np.sin(r[i])
        R = R.dot(lr)
    return R


def translate(pcd, X, Y, Z) -> np.ndarray:
    return np.array(pcd) + np.array((X, Y, Z))[..., np.newaxis]


def rotate_xyz(pcd, rotX, rotY, rotZ) -> np.ndarray:
    return rotMat(np.array((rotX, rotY, rotZ))).dot(pcd)


def rotate_zyx(pcd, rotX, rotY, rotZ) -> np.ndarray:
    return rotMat(np.array((rotX, rotY, rotZ)), order=(2, 1, 0)).dot(pcd)


def count_zero(arr: np.ndarray) -> int:
    return arr.size - np.count_nonzero(arr)


def get_permutations(r_lim: list):
    import itertools

    unique_combinations = []
    permut = itertools.permutations(r_lim, len(r_lim))
    for comb in permut:
        zipped = zip(comb, r_lim)
        unique_combinations.append(list(zipped))

    logging.debug(unique_combinations)
    return unique_combinations


def erode(image: np.ndarray, erosion_level=3, value_range=1) -> np.ndarray:
    """morphological image operation: erosion numpy based implementation

    Args:
        image (np.ndarray): image
        erosion_level (int, optional): erosion level, that is size of the structuring kernel. Defaults to 3.
        value_range (int, optional): value range of the original image: default binary image. Defaults to 1.

    Returns:
        np.array: processed image
    """
    # value_range = 255 # for 8 bit image

    if erosion_level < 3:
        erosion_level = 3
    else:
        erosion_level = erosion_level

    structuring_kernel = np.full(
        shape=(erosion_level, erosion_level), fill_value=value_range
    )

    orig_shape = image.shape
    pad_width = erosion_level - 2

    # pad the matrix with `pad_width`
    image_pad = np.pad(array=image, pad_width=pad_width, mode="constant")
    pimg_shape = image_pad.shape
    h_reduce, w_reduce = (pimg_shape[0] - orig_shape[0]), (
        pimg_shape[1] - orig_shape[1]
    )

    flat_submatrices = []
    for i in range(pimg_shape[0] - h_reduce):
        for j in range(pimg_shape[1] - w_reduce):
            flat_submatrices.append(
                image_pad[i: (i + erosion_level), j: (j + erosion_level)]
            )
    flat_submatrices = np.array(flat_submatrices)

    image_erode = []
    for i in flat_submatrices:
        if (i == structuring_kernel).all():
            image_erode.append(value_range)
        else:
            image_erode.append(0)
    image_erode = np.array(image_erode)

    image_erode = image_erode.reshape(orig_shape)
    return image_erode


# %%


class CalibratioRotationVerification:
    def __init__(
        self,
        dist: np.ndarray,
        dist_noise: np.ndarray,
        modelID3D: int,
        intrinsics3D: np.ndarray,
        extrinsic3D: np.ndarray,
    ) -> None:
        self.dis = dist
        self.dis_noise = dist_noise
        self.modelID3D = modelID3D
        self.intrinsics3D = intrinsics3D
        self.extrinsic3D = extrinsic3D
        self.imager_size = self.dis.transpose().shape

        self.R = rotMat(extrinsic3D[3::])
        self.d_soll_ = self.get_rotated_distances(self.R, np.eye(3))
        self.d_soll_flat = self.apply_dis_mapping(
            self.d_soll_, dis_map=self.dis.flatten()
        )
        self.d_noise_flat = self.apply_dis_mapping(
            d=self.dis_noise.flatten(), dis_map=self.dis.flatten()
        )

    # calculate 3D unit vectors corresponding to each pixel of depth camera
    def get_rotated_distances(self, R: np.ndarray, RR: np.ndarray) -> np.ndarray:
        """get rotated distance map based on two rotation matrices: R, RR

        Args:
            R (np.ndarray): rotation matrix
            RR (np.ndarray): rotation matrix

        Returns:
            np.ndarray: distance image in rotated in user space
        """
        ux, uy, uz = intrinsic_projection(
            self.modelID3D, self.intrinsics3D, *self.imager_size
        )

        e_flatten = np.stack(
            (ux.flatten(), uy.flatten(), uz.flatten()), axis=0)
        e_rot = (RR @ R).dot(e_flatten)
        e_3 = e_rot[-1, :]
        d_rot_flat = -1 / e_3 * self.extrinsic3D[2]

        return d_rot_flat

    def reshape(self, d: np.ndarray, shape=(172, 224)):
        return np.reshape(d, shape)

    def apply_dis_mapping(self, d: np.ndarray, dis_map: np.ndarray):
        d[dis_map > 3.5] = 0
        d[dis_map == 0] = 0
        return d

    def get_dis_map(self, arr: np.ndarray):
        return np.logical_and(arr < 3.5, arr != 0)

    def calculate_d_rotation_bounds(self, r1: int, r2: int) -> tuple:
        """calculate max., min. distance images boundaries based on two rotation angles: roll, pitch

        Args:
            r1 (int): roll angle in deg
            r2 (int): pitch angle in deg

        Returns:
            tuple: rotated distance maps
        """
        d_soll_max = np.array(self.d_soll_flat, copy="True")
        d_soll_min = np.array(self.d_soll_flat, copy="True")

        r_lim = [r1, r2]
        permutations = get_permutations(r_lim)

        for p in permutations:
            for pp in p:

                r = float(pp[0])
                rr = float(pp[1])
                logging.info(f"angle rotations: {r}, {rr}")

                RRe1 = rotMat([r / 180 * np.pi, 0, 0])
                RRe2 = rotMat([0, rr / 180 * np.pi, 0])
                RRe1e2 = RRe1 @ RRe2

                d_soll_flat_RR = self.get_rotated_distances(self.R, RRe1e2)
                d_soll_flat_RR = self.apply_dis_mapping(
                    d_soll_flat_RR, dis_map=self.dis.flatten()
                )
                if np.nanmax(d_soll_flat_RR) > 5:
                    logging.debug(r, rr)
                d_soll_max = np.maximum(d_soll_max, d_soll_flat_RR)
                d_soll_min = np.minimum(d_soll_min, d_soll_flat_RR)

        logging.info(
            f"min allowed abs distance difference from rotation (all pixels) [m]: {np.nanmin(d_soll_min-self.d_soll_flat)}"
        )
        logging.info(
            f"max allowed abs distance difference from rotation (all pixels) [m]: {np.nanmax(d_soll_max-self.d_soll_flat)}"
        )
        return d_soll_min, d_soll_max

    def get_dist_noise_img(self, k: int) -> np.ndarray:
        """apply distance normalization factor to compressed distance image"""
        return k * self.d_noise_flat


def _load_data_h5(filename):
    current_dir = Path(__file__).parent.resolve()

    # Unpack all data required to 2d3d registration
    hf1 = h5py.File(str(current_dir / filename), "r")
    tof = hf1["streams"]["o3r_tof_0"]

    tofIdx = 10
    dis = tof[tofIdx]["distance"] * tof[0]["distanceResolution"]
    dis_noise = tof[tofIdx]["distanceNoise"] * tof[0]["distanceResolution"]
    amp = tof[tofIdx]["amplitude"]
    modelID3D = tof[0]["intrinsicCalibModelID"]
    intrinsics3D = tof[0]["intrinsicCalibModelParameters"]
    extrinsic3D = tof[0]["extrinsicOpticToUserTrans"]
    extrinsic3D = np.append(extrinsic3D, tof[0]["extrinsicOpticToUserRot"])

    json.loads(hf1["streams"]["o3r_json"]["data"][0].tobytes())
    hf1.close()
    return dis, dis_noise, modelID3D, intrinsics3D, extrinsic3D


# %%


def verify_calibration(
    filename: str,
    plot_img: bool = True,
) -> None:

    # load data: ifm h5 data container - for example recording from ifm Vision Assistant
    # file_name_of_recording = "tc_4_1_300_60_pall.h5"

    dis, dis_noise, modelID3D, intrinsics3D, extrinsic3D = _load_data_h5(
        filename)

    calib_verify = CalibratioRotationVerification(
        dist=dis,
        dist_noise=dis_noise,
        modelID3D=modelID3D,
        intrinsics3D=intrinsics3D,
        extrinsic3D=extrinsic3D,
    )

    r_min = -1
    r_max = 1
    d_soll_min, d_soll_max = calib_verify.calculate_d_rotation_bounds(
        r1=r_min, r2=r_max
    )
    dd_max = (d_soll_max + calib_verify.get_dist_noise_img(k=2)
              ).reshape((172, 224))
    dd_min = (d_soll_min - calib_verify.get_dist_noise_img(k=2)
              ).reshape((172, 224))

    if plot_img:
        # angle bisector used for plotting
        angle_bisector = np.array(
            [np.arange(0, 3.5, 0.01), np.arange(0, 3.5, 0.01)])

        # plot 2D based floor distance representation
        plt.figure(1)
        plt.clf()
        plt.plot(
            calib_verify.reshape(calib_verify.d_soll_),
            dd_max,
            "g.",
            label="max allowed",
        )
        plt.plot(
            calib_verify.reshape(calib_verify.d_soll_),
            dd_min,
            "g.",
            label="min allowed",
        )
        plt.plot(calib_verify.reshape(calib_verify.d_soll_),
                 dis, "y.", label="meas")
        plt.plot([0, 3], [0, 3], "r-")
        plt.plot(angle_bisector[0, :], angle_bisector[1, :], "r")
        plt.grid()
        plt.xlabel("expected distance [m]")
        plt.ylabel("measured distance [m]")
        plt.title("Floor distance plot: expected distance vs measured distance")
        plt.savefig("floor_distance_plot_orig.png")

        plt.figure(2)
        plt.clf()
        plt.subplot(1, 2, 1)
        plt.imshow(calib_verify.reshape(d_soll_min))
        plt.colorbar()
        plt.title("min rotation boundary")
        plt.subplot(1, 2, 2)
        plt.imshow(calib_verify.reshape(d_soll_max))
        plt.colorbar()
        plt.title("max rotation boundary")
        plt.suptitle("distance images based on rotated unit vectors")
        plt.savefig("distance_image_based_on_max_rot.png")

    # apply additional distance limits to get valid pixel map:
    # + valid distance have to be < 3.5 m - use 3.5 m threshold for robustness
    # + valid distances != 0
    # + rotated distance map has to be smaller than 3.5 m
    # + rotated distance map != 0
    valid_pixels = (
        (calib_verify.dis < 3.5)
        * (calib_verify.dis != 0)
        * (dd_max.reshape((172, 224)) < 3.5)
        * (dd_min.reshape((172, 224)) > 0)
    )

    # erode the valid pixel map and distance map for robustness (based on rotated distance map)
    valid_pixels_erode = erode(valid_pixels).astype(bool)
    distance_map_erode = erode(
        calib_verify.get_dis_map(arr=dis), erosion_level=3)

    # apply the valid pixel map to rotated distance boundary values to get the valid floor pixel map
    valid_floor = np.where(
        valid_pixels_erode, (dis < dd_max) * (dis > dd_min), 0)

    if plot_img:
        plt.figure(3)
        plt.imshow(valid_floor, interpolation="None")
        plt.colorbar()
        plt.title("Valid floor pixels == 1")
        plt.savefig("valid_floor_pixels.png")

    dist_map_valid_pix = np.count_nonzero(distance_map_erode)
    dist_map_invalid_pix = count_zero(distance_map_erode)
    floor_valid_pix = np.count_nonzero(valid_floor)
    floor_invalid_pix = count_zero(valid_floor)

    if dist_map_valid_pix < 5000:
        raise RuntimeError(
            "Too few valid pixels in the distance measurement: num valid pix - {dist_map_valid_pix}"
        )

    num_invalid_pix = floor_invalid_pix - dist_map_invalid_pix
    logging.info(f"num invalid pixels: {np.abs(num_invalid_pix)}")

    if plot_img:
        plt.figure(5)
        plt.clf()
        plt.imshow(valid_pixels, interpolation="None")
        plt.title(
            "valid pixels based on user input extrinsic calibration and rotation boundaries"
        )
        plt.colorbar()
        plt.savefig("valid_pixel_user_extrinsic_calib.png")

    num_invalid_pix_threshold = 20
    if num_invalid_pix > num_invalid_pix_threshold:
        logger.info(
            f"Number of allowed invlid pixels: {num_invalid_pix_threshold}")
        raise AssertionError(
            f"number of valid pixels larger than threshold: # invalid pix {num_invalid_pix}"
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("numpy").setLevel(logging.WARNING)

    parser = argparse.ArgumentParser(
        prog="Extrinsic Calibration Verification Tool",
        description="Verify the user input extrinsic calibration parameters",
    )

    parser.add_argument("filename")
    parser.add_argument("-p", "--plot_images",
                        default=True, action="store_true")
    args = parser.parse_args()

    verify_calibration(filename=args.filename, plot_img=args.plot_images)

# %%
