#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from ifm3dpy.framegrabber import FrameGrabber, buffer_id
from ifm3dpy.device import O3R
from ifm3dpy.deserialize import TOFInfoV4 as tofv4


def get_frames(o3r):
    fg = FrameGrabber(
        o3r,
        o3r.get(["/ports/port2/data/pcicTCPPort"])["ports"]["port2"]["data"][
            "pcicTCPPort"
        ],
    )

    fg.start([buffer_id.TOF_INFO])

    [ok, data] = fg.wait_for_frame().wait_for(1000)
    return data


o3r = O3R()
config = o3r.get(["/ports/port2/state"])
config["ports"]["port2"]["state"] = "RUN"
o3r.set(config)

data = get_frames(o3r)

import struct

if data.has_buffer(buffer_id.TOF_INFO):
    tof_info = tofv4.deserialize(data.get_buffer(buffer_id.TOF_INFO))
    distance_resolution = tof_info.distance_resolution  # Distance Resolution
    timestamp = tof_info.exposure_timestamps_ns[
        0
    ]  # Timestamp of Exposure Time in NanoSeconds

print(distance_resolution)
print(timestamp)
