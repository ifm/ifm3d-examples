#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
import time
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def callback(frame):
    # Read the distance image and display a pixel in the center
    dist = frame.get_buffer(buffer_id.RADIAL_DISTANCE_IMAGE)
    (height, width) = dist.shape
    print(dist[width // 2, height // 2])

def main(ip, port):
    # Initialize the objects
    o3r = O3R(ip=ip)
    pcic_port = o3r.port(port).pcic_port
    fg = FrameGrabber(o3r, pcic_port=pcic_port)

    # set schema and start Grabber
    fg.start(
        [buffer_id.NORM_AMPLITUDE_IMAGE, buffer_id.RADIAL_DISTANCE_IMAGE, buffer_id.XYZ]
    )

    fg.on_new_frame(callback)

    # Sleep to avoid exiting the program too soon
    time.sleep(1)

    fg.stop()

if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
        PORT = config.PORT_3D

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        PORT = "port2"
    
    main(IP, PORT)
