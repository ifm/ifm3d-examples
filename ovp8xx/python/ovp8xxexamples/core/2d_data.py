#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from functools import partial
import collections
import cv2
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def display(img_queue: collections.deque):
    cv2.startWindowThread()
    cv2.namedWindow("2D image", cv2.WINDOW_NORMAL)
    while True:
        if img_queue:
            cv2.imshow("2D image", img_queue.pop())
            cv2.waitKey(1)


def callback(self, img_queue: collections.deque):
    rgb = cv2.imdecode(self.get_buffer(buffer_id.JPEG_IMAGE), cv2.IMREAD_UNCHANGED)
    img_queue.append(rgb)


def main(ip, port):
    # Initialize the objects
    o3r = O3R(ip)
    pcic_port = o3r.port(port).pcic_port
    fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)

    # Change port to RUN state
    config = o3r.get()
    config["ports"][port]["state"] = "RUN"
    o3r.set(config)
    # Create a queue to store the images
    img_queue = collections.deque(maxlen=10)
    # Register a callback and start streaming frames
    fg.on_new_frame(partial(callback, img_queue=img_queue))
    fg.start([buffer_id.JPEG_IMAGE])
    try:
        display(img_queue)
    except KeyboardInterrupt:
        print("Exiting...")
    # Stop the streaming
    fg.stop()


if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config
        IP = config.IP
        PORT = config.PORT_2D
    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        PORT = "port0"

    main(ip=IP, port=PORT)
