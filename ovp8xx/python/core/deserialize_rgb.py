# -*- coding: utf-8 -*-
#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This examples shows how to use the deserializer module
# to extract data from the RGBInfoV1 buffer.
# The same principles can be applied to deserialize data from
# other buffers (see accompanying documentation for mode details)
#################################################################
# Import the relevant modules
from ifm3dpy.deserialize import RGBInfoV1
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def main(IP):
    ###########################
    # Create the O3R and FrameGrabber
    # and choose which images
    # to receive
    ###########################
    o3r = O3R(IP)
    # Assuming PORT is a 2D port
    pcic_port = None
    for port in o3r.ports():
        if port.type == "2D":
            # Get the first 2D port
            print(f"Using first available 2D Port {port.port}")
            pcic_port = port.pcic_port
            break

    if pcic_port is None:
        print("No 2D port found")
        return

    fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)
    # Define the images to receive when starting the data stream
    fg.start([buffer_id.RGB_INFO])
    try:
        # Get a frame
        [ok, frame] = fg.wait_for_frame().wait_for(500)
        # Retrieve the data from the relevant buffer
        if ok:
            rgb_info_buffer = frame.get_buffer(buffer_id.RGB_INFO)
        else:
            raise TimeoutError
    except Exception as e:
        raise e
    fg.stop()
    ###############################
    # Extract data from the buffer
    # Using the deserializer module
    ###############################
    rgb_info = RGBInfoV1()
    rgb_info_deser = rgb_info.deserialize(rgb_info_buffer)
    print("Sample of data available in the RGBInfoV1 buffer:")
    print(f"RGB info timestamp: {rgb_info_deser.timestamp_ns}")
    print(f"Exposure time used for rgb images: {rgb_info_deser.exposure_time}")
    print(
        f"RGB intrinsic calibration model id: {rgb_info_deser.intrinsic_calibration.model_id}"
    )
    print(
        f"RGB intrinsic calibration parameters: {rgb_info_deser.intrinsic_calibration.parameters}"
    )


if __name__ == "__main__":
    IP = "192.168.0.69"
    main(IP=IP)
