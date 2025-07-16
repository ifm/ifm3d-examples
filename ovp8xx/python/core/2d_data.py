# -*- coding: utf-8 -*-
#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import collections
from functools import partial
from time import perf_counter

import cv2
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def display(img_queue: collections.deque, timeout: int):
    """
    Display the images from the queue in a window.
    Args:
        img_queue (collections.deque): Queue containing the images to be displayed.
        timeout (int): Timeout in milliseconds for frame grabbing.
    """
    # Create a window to display the images
    cv2.startWindowThread()
    cv2.namedWindow("2D image", cv2.WINDOW_NORMAL)
    start = perf_counter()
    while (perf_counter() - start) * 1000 <= timeout:
        if img_queue:
            cv2.imshow("2D image", img_queue.pop())
            cv2.waitKey(1)


def callback(self, img_queue: collections.deque):
    """Callback function to be called when a new frame is available.

    Args:
        img_queue (collections.deque): Queue to store the images.
    """
    # Get the image from the buffer and decode it
    rgb = cv2.imdecode(self.get_buffer(buffer_id.JPEG_IMAGE), cv2.IMREAD_UNCHANGED)
    img_queue.append(rgb)


def main(ip: str, port: str, queue_length: int, timeout: int):
    """
    Main function to initialize the O3R device, set the port to RUN state,
    and start streaming frames to a queue.
    Args:
        ip (str): IP address of the O3R device.
        port (str): Port name to be set to RUN state.
        queue_length (int): Maximum length of the image queue.
        timeout (int): Timeout in milliseconds for frame grabbing.
    """
    # Initialize the O3R device
    o3r = O3R(ip)
    pcic_port = o3r.port(port).pcic_port
    fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)

    # Change port to RUN state
    config = o3r.get()
    config["ports"][port]["state"] = "RUN"
    o3r.set(config)

    # Create a queue to store the images
    img_queue = collections.deque(maxlen=queue_length)

    # Register a callback and start streaming frames
    fg.on_new_frame(partial(callback, img_queue=img_queue))
    fg.start([buffer_id.JPEG_IMAGE])

    try:
        while True:
            display(img_queue, timeout)
    except KeyboardInterrupt:
        print("Exiting...")

    # Stop the streaming
    fg.stop()


if __name__ == "__main__":
    IP = "192.168.0.69"
    PORT = "port0"
    queue_length = 5
    timeout_ms = 300
    main(ip=IP, port=PORT, queue_length=queue_length, timeout=timeout_ms)
