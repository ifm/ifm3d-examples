#!/usr/bin/env python3
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
import os
import logging
import time

import matplotlib.pyplot as plt
from matplotlib import gridspec

from ifm3dpy.device import Device
from ifm3dpy.framegrabber import FrameGrabber, buffer_id

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")


def main(ip):
    # Add IP address of the camera to no-proxy environment variables
    os.environ["NO_PROXY"] = ip

    # Initialize the objects
    device = Device(ip)
    fg = FrameGrabber(device)

    # Set schema and start FrameGrabber
    # Due to a known issue, for the O3X device both the
    # NORM_AMPLITUDE_IMAGE and the AMPLITUDE_IMAGE buffers
    # have to be requested.
    fg.start(
        [
            buffer_id.NORM_AMPLITUDE_IMAGE,
            buffer_id.RADIAL_DISTANCE_IMAGE,
            buffer_id.CONFIDENCE_IMAGE,
            buffer_id.AMPLITUDE_IMAGE,
        ]
    )
    time.sleep(3)  # Grace period after starting the data stream

    trigger_mode = device.to_json()["ifm3d"]["Apps"][0]["TriggerMode"]

    if trigger_mode == "1":
        logger.info("Camera is in Continuous Trigger Mode")
    elif trigger_mode == "2":
        logger.info("Camera is in Software Trigger Mode")
        # Software Trigger the camera
        fg.sw_trigger()

    [ok, frame] = fg.wait_for_frame().wait_for(1500)

    if not ok:
        raise RuntimeError("Timeout while waiting for a frame.")

    radial_distance = frame.get_buffer(buffer_id.RADIAL_DISTANCE_IMAGE)
    amplitude = frame.get_buffer(buffer_id.NORM_AMPLITUDE_IMAGE)
    confidence = frame.get_buffer(buffer_id.CONFIDENCE_IMAGE)

    # Create a figure
    fig = plt.figure(figsize=(10, 8))

    # Define the grid layout
    gs = gridspec.GridSpec(2, 2, height_ratios=[1, 2])
    ax1 = fig.add_subplot(gs[0, 0])
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, :])

    ax1.imshow(radial_distance, cmap="jet")
    ax1.set_title("Radial Distance Image")
    ax1.axis("off")

    ax2.imshow(amplitude, cmap="gray")
    ax2.set_title("Amplitude Image")
    ax2.axis("off")

    ax3.imshow(confidence, cmap="jet")
    ax3.set_title("Confidence Image")
    ax3.axis("off")

    plt.tight_layout()
    plt.show()

    fg.stop()


if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from o3d3xx_o3x1xx_examples import config

        IP = config.IP

    except ImportError:
        # Otherwise, use default values
        logger.info(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        logger.info("Defaulting to the default configuration.")
        IP = "192.168.0.69"
    main(ip=IP)
