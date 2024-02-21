"""
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 
 How to: receive data from multiple heads
 One feature of the O3R platform is to enable the use of multiple camera heads
 of different types (2D, 3D, various resolutions, etc). In this example, we
 show how to retrieve the pcic port number for each head connected to the VPU
 along with its type, create `FrameGrabber` objects and get a frame for each.
"""

from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id
import cv2
import matplotlib.pyplot as plt

def main(ip):
    o3r = O3R(ip)

    fgs = []
    types = []
    print("Available connections:")
    for port in o3r.get(["/ports"])["ports"]:
        # exclude port 6, since it is the IMU port
        if port != "port6":
            pcic = o3r.get(["/ports/" + port + "/data/pcicTCPPort"])["ports"][port]["data"][
                "pcicTCPPort"
            ]
            data_type = o3r.get(["/ports/" + port + "/info/features/type"])["ports"][port][
                "info"
            ]["features"]["type"]
            fg = FrameGrabber(o3r, pcic_port=pcic)
            if data_type == "2D":
                types.append("2D")
                fg.start([buffer_id.JPEG_IMAGE])
                print("Port: {}   PCIC: {}    Type: {}".format(port, pcic, data_type))
            elif data_type == "3D":
                types.append("3D")
                fg.start([buffer_id.RADIAL_DISTANCE_IMAGE])
                print("Port: {}   PCIC: {}    Type: {}".format(port, pcic, data_type))
            fgs.append(fg)
    # Grab frames from each head
    for fg in fgs:
        [ok, frame] = fg.wait_for_frame().wait_for(3000)
        if ok:
            print(
                "Timestamp of frame {}: {}".format(
                    frame.frame_count(), frame.timestamps()[0]
                )
            )
            # Display the image
            plt.figure()
            if types[i] == "2D":
                # The image needs to be converted to RGB to be displayed.
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
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"


    main(ip=IP)