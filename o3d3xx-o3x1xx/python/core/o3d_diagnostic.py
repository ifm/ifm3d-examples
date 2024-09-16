#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# This example shows how to unpack diagnostic
# data from the O3D camera.
# The diagnostic data provides important
# information about the camera's internal state,
# such as the temperature.

# Necessary imports
import logging
import struct
import time
from ifm3dpy.device import O3D
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


logger = logging.getLogger(__name__)


def main(ip):
    # Create the objects
    o3d = O3D(ip=ip)
    fg = FrameGrabber(o3d, int(o3d.device_parameter("PcicTcpPort")))

    # Collect a frame
    fg.start(
        [
            buffer_id.DIAGNOSTIC,
        ]
    )
    time.sleep(5)  # Grace period after initialization of the data stream
    [ok, frame] = fg.wait_for_frame().wait_for(500)
    if not ok:
        raise Exception("Timeout waiting for frame")

    # Get the data from the collected frame
    data = frame.get_buffer(buffer_id.DIAGNOSTIC)

    # Unpack the data
    unpacked_data = struct.unpack("<4i2I", data)
    logger.info(f"Diagnostic data:")
    logger.info(
        f"Illumination temperature (0.1 °C), invalid = 32767: {unpacked_data[0]}"
    )
    logger.info(f"Frontend temperature 1 (0.1 °C), invalid = 32767: {unpacked_data[1]}")
    logger.info(f"Frontend temperature 2 (0.1 °C), invalid = 32767: {unpacked_data[2]}")
    logger.info(f"i.mx6 Temperature (0.1 °C), invalid = 32767: {unpacked_data[3]}")
    logger.info(f"Frame duration: {unpacked_data[4]}")
    logger.info(f"Framerate: {unpacked_data[5]}")
    fg.stop()


if __name__ == "__main__":
    # EDIT here when using a non-default IP address
    IP = "192.168.0.69"
    logging.basicConfig(level=logging.INFO)
    main(IP)
