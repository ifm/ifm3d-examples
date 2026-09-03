# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#%%############################################
if __name__ != "__main__":
    print(
        """
############ O3D example code ###############
      Script was accidentally imported.
  Simply run the code directly as a script,
        or interactively. Exiting...
#############################################
"""
    )
    exit(0)
#############################################
# This example shows how to unpack diagnostic
# data from the O3D camera.
# The diagnostic data provides important
# information about the camera's internal state,
# such as the temperature.

import logging
import time

from ifm3dpy.device import O3D
from ifm3dpy.framegrabber import FrameGrabber, buffer_id

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

ip = "192.168.0.69"

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
raw = frame.get_buffer(buffer_id.DIAGNOSTIC)
#%%
#%%
# Ensure raw is bytes and unpack like the C++ example (4 x int32, 2 x uint32)
import struct

# Convert various buffer types to bytes
if isinstance(raw, (bytes, bytearray)):
    data = bytes(raw)
elif isinstance(raw, memoryview):
    data = raw.tobytes()
elif hasattr(raw, "tobytes"):
    data = raw.tobytes()
else:
    data = bytes(raw)

# diagnostic layout: four signed 32-bit values followed by two unsigned 32-bit values
fmt = "<4i2I"
expected = struct.calcsize(fmt)

if len(data) < expected:
    raise ValueError(
        f"Diagnostic buffer too short: got {len(data)} bytes, expected at least {expected}"
    )

try:
    unpacked = struct.unpack(fmt, data[:expected])
except struct.error as e:
    raise RuntimeError(f"Failed to unpack diagnostic data: {e}")

illum_temp = unpacked[0]
front_temp1 = unpacked[1]
front_temp2 = unpacked[2]
imx6_temp = unpacked[3]
frame_duration = unpacked[4]
framerate = unpacked[5]

invalid_value = 32767  # sentinel used in examples

logger.info(
    f"Illumination temperature (0.1 °C), invalid = {invalid_value}: {illum_temp}"
)
logger.info(
    f"Frontend temperature 1 (0.1 °C), invalid = {invalid_value}: {front_temp1}"
)
logger.info(
    f"Frontend temperature 2 (0.1 °C), invalid = {invalid_value}: {front_temp2}"
)
logger.info(f"i.mx6 Temperature (0.1 °C), invalid = {invalid_value}: {imx6_temp}")
logger.info(f"Frame duration: {frame_duration} µs")
logger.info(f"Framerate: {framerate}")
fg.stop()


# %%
