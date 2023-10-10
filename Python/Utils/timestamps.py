#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This examples shows how to retrieve image
# timestamps for the O3R.
# In a second part it inspects timestamps for
# a system synchronized with NTP. This relies
# on an internet connection on the local machine.

# Expected setup:
# RGB camera in port 0
# 3D camera in port 2
import time
import datetime

from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id
from ifm3dpy.deserialize import TOFInfoV4, RGBInfoV1

# IP configuration
LOCAL_IP = "192.168.0.111"  # Used for NTP synchronization
O3R_IP = "192.168.0.69"
# Change port numbers here for a different setup
PORT_2D = "port0"
PORT_3D = "port2"

o3r = O3R(O3R_IP)
PCIC_PORT_2D = o3r.get([f"/ports/{PORT_2D}/data/pcicTCPPort"])["ports"][PORT_2D][
    "data"
]["pcicTCPPort"]
PCIC_PORT_3D = o3r.get([f"/ports/{PORT_3D}/data/pcicTCPPort"])["ports"][PORT_3D][
    "data"
]["pcicTCPPort"]

fg_2d = FrameGrabber(o3r, pcic_port=PCIC_PORT_2D)
fg_3d = FrameGrabber(o3r, pcic_port=PCIC_PORT_3D)

epoch = datetime.datetime.utcfromtimestamp(0).astimezone(datetime.timezone.utc)
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
    f"Acquisition to reception latency:   {abs(rgb_info.timestamp_ns - frame_ts*1e9):.0f}"
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
    f"Last exposure acquisition to reception latency: {abs(tof_info.exposure_timestamps_ns[0] - frame_ts*1e9):.0f}"
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
curr_time_o3r = o3r.get(["/device/clock/currentTime"])["device"]["clock"]["currentTime"]
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
    f"Last exposure acquisition to reception latency: {abs(tof_info.exposure_timestamps_ns[0] - frame_ts*1e9):.0f}"
)