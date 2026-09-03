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

WINDOW_NAME = "2D image"


def window_open(window_name: str = WINDOW_NAME) -> bool:
    """Return True while the OpenCV window is still visible."""
    try:
        return cv2.getWindowProperty(window_name, cv2.WND_PROP_VISIBLE) >= 1
    except cv2.error:
        return False


def show_stream(img_queue: collections.deque):
    """Display the latest image until the window is closed or q/ESC is pressed."""
    cv2.startWindowThread()
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    while window_open():
        if img_queue:
            cv2.imshow(WINDOW_NAME, img_queue.pop())

        key = cv2.waitKey(1) & 0xFF
        if key in (27, ord("q")):
            break


def save_first_image(
    img_queue: collections.deque, timeout: int, save_path: str
) -> bool:
    """Save the first received image within the timeout."""
    deadline = perf_counter() + timeout / 1000
    while perf_counter() < deadline:
        if img_queue:
            cv2.imwrite(save_path, img_queue.pop())
            print(f"Image saved to: {save_path}")
            return True
        cv2.waitKey(1)

    print(f"ERROR: No image received within {timeout} ms.")
    return False


def callback(self, img_queue: collections.deque):
    """Callback function to be called when a new frame is available.

    Args:
        img_queue (collections.deque): Queue to store the images.
    """
    # Get the image from the buffer and decode it
    rgb = cv2.imdecode(self.get_buffer(buffer_id.JPEG_IMAGE), cv2.IMREAD_UNCHANGED)
    img_queue.append(rgb)


def find_first_2d_stream(o3r: O3R):
    """Return the first available 2D port and ensure it is in RUN state."""
    port = next((port for port in o3r.ports() if port.type == "2D"), None)
    if port is None:
        raise RuntimeError("No 2D port found.")

    state = o3r.get([f"/ports/{port.port}/state"])["ports"][port.port]["state"]
    if state != "RUN":
        print(f"Changing {port.port} from {state} to RUN")
        o3r.set({"ports": {port.port: {"state": "RUN"}}})

    print(f"Found 2D stream on port {port.port} (PCIC port {port.pcic_port})")
    return port


def main(ip: str, queue_length: int, timeout: int, save_path: str = None):
    """Open the first 2D stream, display it, or save the first image."""
    o3r = O3R(ip)
    try:
        port = find_first_2d_stream(o3r)
    except RuntimeError as error:
        print(f"ERROR: {error}")
        return

    img_queue = collections.deque(maxlen=queue_length)
    fg = FrameGrabber(cam=o3r, pcic_port=port.pcic_port)

    fg.on_new_frame(partial(callback, img_queue=img_queue))
    fg.start([buffer_id.JPEG_IMAGE])

    try:
        if save_path:
            save_first_image(img_queue, timeout, save_path)
        else:
            show_stream(img_queue)
            print("Display window closed. Exiting...")
    except KeyboardInterrupt:
        print("Exiting...")
    finally:
        fg.stop().wait()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    IP = "192.168.0.69"
    queue_length = 5
    timeout_ms = 300
    # Set to a path like "output.jpg" to save the first image and exit, or None to display the stream
    save_image_path = None
    main(
        ip=IP, queue_length=queue_length, timeout=timeout_ms, save_path=save_image_path
    )
