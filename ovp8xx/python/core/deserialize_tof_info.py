# -*- coding: utf-8 -*-
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This examples shows how to use the deserializer module
# to extract data from the TOFInfoV4 buffer.
#################################################################
# Import the relevant modules
from ifm3dpy.deserialize import TOFInfoV4
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def main(IP: str) -> None:
    ###########################
    # Create the O3R and FrameGrabber
    # and choose which images to receive.
    # In this example we only receive one frame.
    ###########################
    o3r = O3R(IP)

    CONFIG = o3r.get()
    PCIC_PORT = None

    # Get the first available 3D port
    for port in o3r.ports():
        if port.type == "3D":
            # Get the first 3D port
            print(f"Using first available 3D Port {port.port}")
            PORT = port.port
            PCIC_PORT = port.pcic_port
            break

    if PORT is None:
        print("No 3D port found")
        return

    STATE = CONFIG["ports"][f"{PORT}"]["state"]
    if STATE != "RUN":
        print(f"Port {PORT} is in {STATE} state and not in RUN state")
        print("Set the camera RUN state")
        o3r.set({"ports": {f"{PORT}": {"state": "RUN"}}})

    fg = FrameGrabber(cam=o3r, pcic_port=PCIC_PORT)
    # Define the images to receive when starting the data stream
    fg.start([buffer_id.TOF_INFO])
    # Get a frame
    [ok, frame] = fg.wait_for_frame().wait_for(500)
    # Raise timeout error is not frame is received
    if not ok:
        raise TimeoutError(
            "No frame received, make sure the camera is not in ERROR state"
        )

    fg.stop()
    ###############################
    # Extract data from the buffer
    # Using the deserializer module
    ###############################
    tof_info = TOFInfoV4().deserialize(frame.get_buffer(buffer_id.TOF_INFO))
    print("Sample of data available in the TOFInfoV4 buffer:")
    print(f"Current minimum measurement range: {tof_info.measurement_range_min} m")
    print(f"Current maximum measurement range: {tof_info.measurement_range_max} m")
    print(f"Temperature of the illumination module: {tof_info.illu_temperature}")


if __name__ == "__main__":
    IP = "192.168.0.69"
    main(IP=IP)
