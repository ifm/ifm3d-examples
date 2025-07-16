# -*- coding: utf-8 -*-
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# This example shows how to find out what the
# data format is for a given buffer_id.
import logging

import numpy as np
from ifm3dpy.device import O3R, Device
from ifm3dpy.framegrabber import FrameGrabber, buffer_id

logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main(ip: str):
    # Create a device object
    device = Device(ip)
    ##########################################
    # Here, we need to know which device we are
    # connecting to so that we can pick the proper port.
    ##########################################
    device_type = device.who_am_i()
    if device_type == device.device_family.O3D:
        pcic_port = device.device_parameter("PcicTcpPort")
    elif device_type == device.device_family.O3X:
        pcic_port = device.device_parameter("PcicTcpPort")
    elif device_type == device.device_family.O3R:
        # We pick the first available 3D port
        pcic_port = next(
            (port.pcic_port for port in O3R().ports() if port.type == "3D"), None
        )
        if pcic_port is None:
            raise ValueError("No 3D port found on the O3R")
    else:
        raise TypeError(f"Unknown device type: {device_type}")

    #########################################
    # Create a framegrabber, start the data
    # stream and collect a frame
    ##########################################
    fg = FrameGrabber(device, pcic_port)
    # The buffer_id.XYZ is common for all three devices,
    # so we will use this one for the example.
    # The example applies for all the buffer_ids.
    fg.start([buffer_id.XYZ])

    # Get a frame
    [ok, frame] = fg.wait_for_frame().wait_for(1000)

    if not ok:
        raise TimeoutError(
            "Timeout waiting for frame. Make sure you are using the continuous mode."
        )
    ##########################################
    # Get the data from the frame and display
    # the data format
    ##########################################
    xyz = frame.get_buffer(buffer_id.XYZ)

    # Print the data format
    logger.info(type(xyz))
    logger.info(np.shape(xyz))
    logger.info(xyz.dtype)


if __name__ == "__main__":
    # EDIT FOR YOUR SETUP
    IP = "192.168.0.69"

    main(IP)
