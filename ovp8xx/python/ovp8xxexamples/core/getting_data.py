#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def main(IP, PORT):
    # Initialize the objects
    o3r = O3R(IP)
    fg = FrameGrabber(o3r, pcic_port=PORT)

    # Set schema and start Grabber
    fg.start(
        [buffer_id.NORM_AMPLITUDE_IMAGE, buffer_id.RADIAL_DISTANCE_IMAGE, buffer_id.XYZ]
    )

    # Get a frame
    [ok, frame] = fg.wait_for_frame().wait_for(1500)  # wait with 1500ms timeout

    # Check that a frame was received
    if not ok:
        raise RuntimeError("Timeout while waiting for a frame.")

    # Read the distance image and display a pixel in the center
    dist = frame.get_buffer(buffer_id.RADIAL_DISTANCE_IMAGE)
    (width, height) = dist.shape
    print(dist[width // 2, height // 2])
    fg.stop()


if __name__ == "__main__":
    IP="192.168.0.69"
    PORT=50012
    main(IP=IP, PORT=PORT)
