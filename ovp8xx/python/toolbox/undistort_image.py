# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This example demonstrates how to undistort images
# from the O3R225 (3D + RGB) and O3R222 (RGB only) camera heads.

from io import BytesIO

import matplotlib.pyplot as plt
import numpy as np
import scipy.ndimage as ndi
from ifm3dpy.deserialize import RGBInfoV1, TOFInfoV4
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id
from o3r_algo_utilities.o3r_uncompress_di import (
    evalIntrinsicCoords,
    evalIntrinsicCoordsReverse,
)
from PIL import Image


def plot_comparison(original_image, undistorted_image, image_type="Image"):
    """
    Plot side-by-side comparison of original and undistorted images.

    Args:
        original_image: Original distorted image
        undistorted_image: Undistorted image
        image_type: Type of image (e.g., "Image", "Distance") for titles
    """
    plt.figure(figsize=(12, 6))
    plt.subplot(1, 2, 1)
    plt.imshow(original_image)
    plt.axis("off")
    plt.title(f"Distorted {image_type}")

    plt.subplot(1, 2, 2)
    plt.imshow(undistorted_image)
    plt.axis("off")
    plt.title(f"Undistorted {image_type}")

    plt.show()


def undistort(
    image: np.ndarray, intrinsic_calibration, inverse_intrinsic_calibration
) -> np.ndarray:
    """
    Undistort an image using the intrinsic and inverse intrinsic calibration.
    Works with both single-channel (e.g. distance) and multi-channel (e.g. RGB) images.

    Args:
        image: Input image, 2D (H, W) or 3D (H, W, C).
        intrinsic_calibration: Intrinsic calibration from the camera info buffer.
        inverse_intrinsic_calibration: Inverse intrinsic calibration from the camera info buffer.

    Returns:
        Undistorted image with the same shape and dtype as the input.
    """
    # Build a pinhole target model: keep focal length and principal point, zero out distortion
    target_model_id = 0
    target_model_params = [0] * len(intrinsic_calibration.parameters)
    target_model_params[:4] = intrinsic_calibration.parameters[:4]

    rectified = np.zeros_like(image)

    # Compute the pixel mapping (2D indices only)
    h, w = image.shape[:2]
    vx, vy, vz = evalIntrinsicCoords(
        target_model_id, target_model_params, *np.indices((h, w))
    )
    imgy, imgx = evalIntrinsicCoordsReverse(
        inverse_intrinsic_calibration.model_id,
        inverse_intrinsic_calibration.parameters,
        vx,
        vy,
        vz,
    )

    # Apply mapping: per-channel for multi-channel images, directly for single-channel
    is_float = np.issubdtype(image.dtype, np.floating)
    cval = np.nan if is_float else 0

    if image.ndim == 3:
        for ch in range(image.shape[2]):
            ndi.map_coordinates(
                image[:, :, ch],
                (imgy, imgx),
                output=rectified[:, :, ch],
                order=1,
                mode="constant",
                cval=cval,
            )
    else:
        ndi.map_coordinates(
            image, (imgy, imgx), output=rectified, order=1, mode="constant", cval=cval
        )

    return rectified


def main(ip: str = "192.168.0.69", port: str = "port5") -> None:
    """
    Main function to undistort images from the specified port and display comparisons.
     - For 2D ports, it undistorts the RGB image.
     - For 3D ports, it undistorts the distance image.
     The function also handles exceptions and ensures proper cleanup of resources.
    """

    try:
        o3r = O3R(ip)
        port_type = o3r.port(port).type
        pcic_port = o3r.port(port).pcic_port
        fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)
        if port_type == "2D":
            print(f"Using specified 2D Port {port}")
            fg.start([buffer_id.JPEG_IMAGE, buffer_id.RGB_INFO])
            ok, frame = fg.wait_for_frame().wait_for(500)
            if not ok:
                raise RuntimeError("Failed to get frame")
            rgb_image_buffer = frame.get_buffer(buffer_id.JPEG_IMAGE)
            rgb_image_info_buffer = frame.get_buffer(buffer_id.RGB_INFO)
            rgb_image = np.array(Image.open(BytesIO(rgb_image_buffer)))
            rgb_info = RGBInfoV1().deserialize(rgb_image_info_buffer)

            rgb_image_rectified = undistort(
                rgb_image,
                rgb_info.intrinsic_calibration,
                rgb_info.inverse_intrinsic_calibration,
            )

            plot_comparison(rgb_image, rgb_image_rectified, "RGB Image")

        elif port_type == "3D":
            print(f"Using specified 3D Port {port}")
            fg.start(
                [
                    buffer_id.RADIAL_DISTANCE_IMAGE,
                    buffer_id.NORM_AMPLITUDE_IMAGE,
                    buffer_id.TOF_INFO,
                ]
            ).wait()

            ok, frame = fg.wait_for_frame().wait_for(500)
            if not ok:
                raise RuntimeError("Failed to get frame")
            distance_image = frame.get_buffer(buffer_id.RADIAL_DISTANCE_IMAGE)
            amplitude_image = frame.get_buffer(buffer_id.NORM_AMPLITUDE_IMAGE)

            # Mark invalid pixels as NaN before undistortion
            amplitude_image[amplitude_image < 0] = np.nan
            distance_image[distance_image <= 0] = np.nan

            tof_info_buffer = frame.get_buffer(buffer_id.TOF_INFO)
            tof_info = TOFInfoV4().deserialize(tof_info_buffer)

            distance_image_rectified = undistort(
                distance_image,
                tof_info.intrinsic_calibration,
                tof_info.inverse_intrinsic_calibration,
            )
            amplitude_image_rectified = undistort(
                amplitude_image,
                tof_info.intrinsic_calibration,
                tof_info.inverse_intrinsic_calibration,
            )

            plot_comparison(distance_image, distance_image_rectified, "Distance")
            plot_comparison(amplitude_image, amplitude_image_rectified, "Amplitude")
        else:
            raise ValueError(f"Port {port} is not a valid 2D or 3D port")
    except Exception as e:
        raise RuntimeError(f"Could not get port {port}") from e
    finally:
        fg.stop()
        o3r = None
        fg = None


if __name__ == "__main__":
    IP = "192.168.0.69"
    PORT = "port0"  # Can be 2D or 3D port

    main(IP, PORT)
