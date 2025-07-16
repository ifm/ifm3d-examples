# -*- coding: utf-8 -*-
#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This examples shows how to retrieve image
# timestamps for the O3R.
# In a second part it inspects timestamps for
# a system synchronized with NTP. This relies
# on an internet connection on the local machine.

import datetime

# Expected setup:
# RGB camera in port 0
# 3D camera in port 2
import time

from ifm3dpy.deserialize import RGBInfoV1, TOFInfoV4
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def main(local_ip, o3r_ip, port_2d, port_3d):
    PORT_2D = port_2d
    PORT_3D = port_3d
    O3R_IP = o3r_ip
    LOCAL_IP = local_ip
    o3r = O3R(O3R_IP)
    for ports in o3r.ports():
        if ports.port == PORT_2D:
            PCIC_PORT_2D = ports.pcic_port
        if ports.port == PORT_3D:
            PCIC_PORT_3D = ports.pcic_port

    fg_2d = FrameGrabber(o3r, pcic_port=PCIC_PORT_2D)
    fg_3d = FrameGrabber(o3r, pcic_port=PCIC_PORT_3D)

    epoch = datetime.datetime.fromtimestamp(0, datetime.timezone.utc)
    local_tz = datetime.datetime.now(datetime.timezone.utc).astimezone().tzinfo
    print("All the timestamps are displayed in nanoseconds since epoch.")
    print(f"Epoch date in UTC: {epoch}")
    print(f"Local time zone: {local_tz}")
    print("/////////////////////////////////")
    ####################
    # For the 2D camera
    ####################
    fg_2d.start([buffer_id.RGB_INFO])
    [ok, frame] = fg_2d.wait_for_frame().wait_for(1000)

    if not ok:
        raise RuntimeError("Timeout while waiting for a RGB_INFO.")

    fg_2d.stop()

    # Get the acquisition timestamps
    rgb_info = RGBInfoV1().deserialize(frame.get_buffer(buffer_id.RGB_INFO))
    # Convert frame datetime to timestamp since epoch
    frame_ts = frame.timestamps()[0].timestamp()
    # Display results
    print(f"2D acquisition timestamp:           {rgb_info.timestamp_ns}")
    print(f"2D receive timestamp:               {frame_ts*1e9:.0f}")
    print(
        f"Acquisition to reception latency:   {abs(int(rgb_info.timestamp_ns) - int(frame_ts*1e9)):.0f}"
    )
    print("/////////////////////////////////")
    ####################
    # For the 3D camera
    ####################
    fg_3d.start([buffer_id.TOF_INFO])
    [ok, frame] = fg_3d.wait_for_frame().wait_for(1000)

    if not ok:
        raise RuntimeError("Timeout while waiting for a TOF_INFO.")

    fg_3d.stop()
    tof_info = TOFInfoV4().deserialize(frame.get_buffer(buffer_id.TOF_INFO))
    frame_ts = frame.timestamps()[0].timestamp()
    print(
        f"3D acquisition timestamps:                      {tof_info.exposure_timestamps_ns}"
    )
    print(f"3D reception timestamps:                        {frame_ts*1e9:.0f}")
    print(
        f"Last exposure acquisition to reception latency: {abs(int(tof_info.exposure_timestamps_ns[0]) - int(frame_ts*1e9)):.0f}"
    )

    print("/////////////////////////////////")
    ##########################################
    # Inspecting timestamps with sNTP enabled
    ##########################################
    print("Enabling NTP synchronization on the device.")
    print("Make sure you activate the NTP server on your local machine.")
    o3r.set({"device": {"clock": {"sntp": {"availableServers": [f"{LOCAL_IP}"]}}}})
    time.sleep(3)
    curr_local_time = datetime.datetime.now().timestamp() * 1e9
    curr_time_o3r = o3r.get(["/device/clock/currentTime"])["device"]["clock"][
        "currentTime"
    ]
    print(f"Current local timestamp:    {curr_local_time:.0f}")
    print(f"Current time on device:     {int(curr_time_o3r)}")

    fg_3d.start([buffer_id.TOF_INFO])
    [ok, frame] = fg_3d.wait_for_frame().wait_for(1000)

    if not ok:
        raise RuntimeError("Timeout while waiting for a TOF_INFO.")

    fg_3d.stop()

    tof_info = TOFInfoV4().deserialize(frame.get_buffer(buffer_id.TOF_INFO))
    frame_ts = frame.timestamps()[0].timestamp()
    print(
        f"3D acquisition timestamps (with sNTP):          {tof_info.exposure_timestamps_ns}"
    )
    print(f"3D reception timestamps (with sNTP):            {frame_ts*1e9:.0f}")
    print(
        f"Last exposure acquisition to reception latency: "
        f"{abs(int(tof_info.exposure_timestamps_ns[0]) - int(frame_ts*1e9)):.0f} ns"
    )


if __name__ == "__main__":
    LOCAL_IP = "192.168.0.200"
    O3R_IP = "192.168.0.69"
    PORT_2D = "port0"
    PORT_3D = "port2"

    main(local_ip=LOCAL_IP, o3r_ip=O3R_IP, port_2d=PORT_2D, port_3d=PORT_3D)
