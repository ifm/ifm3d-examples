# -*- coding: utf-8 -*-
# ################################################
# * Copyright 2024-present ifm electronic, gmbh
# * SPDX-License-Identifier: Apache-2.0
#
# How to: receive data from multiple heads
# One feature of the O3R platform is to enable the use of multiple camera heads
# of different types (2D, 3D, various resolutions, etc). In this example, we
# show how to retrieve the pcic port number for each head connected to the VPU
# along with its type, create `FrameGrabber` objects and get a frame for each.


import cv2
import matplotlib.pyplot as plt
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def main(ip):
    o3r = O3R(ip)

    fgs = []
    types = []
    print("Available connections:")

    for port in o3r.ports():
        if port.port == "port6":  # skipping IMU port
            continue

        pcic = port.pcic_port
        data_type = port.type
        fg = FrameGrabber(o3r, pcic_port=pcic)

        if data_type == "2D":
            types.append("2D")
            fg.start([buffer_id.JPEG_IMAGE])
        elif data_type == "3D":
            types.append("3D")
            fg.start([buffer_id.RADIAL_DISTANCE_IMAGE])
        else:
            continue  # Skip unsupported types

        print(f"Port: {port.port}   PCIC: {pcic}    Type: {data_type}")
        fgs.append(fg)

    # Grab frames from each head
    for fg, type in zip(fgs, types):
        [ok, frame] = fg.wait_for_frame().wait_for(3000)
        if ok:
            print(f"Timestamp of frame {frame.frame_count()}: {frame.timestamps()[0]}")
            plt.figure()
            if type == "2D":
                img = cv2.imdecode(
                    frame.get_buffer(buffer_id.JPEG_IMAGE), cv2.IMREAD_UNCHANGED
                )
            else:
                img = frame.get_buffer(buffer_id.RADIAL_DISTANCE_IMAGE)
            plt.imshow(img)
            plt.show()
        else:
            print("Timeout waiting for camera!")

    # Stop the framegrabbers
    for fg in fgs:
        fg.stop()


if __name__ == "__main__":
    IP = "192.168.0.69"
    main(ip=IP)
