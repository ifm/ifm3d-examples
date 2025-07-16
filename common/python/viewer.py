# -*- coding: utf-8 -*-
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
"""This program is a small viewer that can
be used to display amplitude, distance, xyz or JPEG
images from any of the supported devices (O3X, O3D and O3R).
The JPEG image is only supported for the O3R platform.
"""

import argparse
import collections
import logging
import time
from functools import partial
from typing import Callable

import cv2
from ifm3dpy.device import O3R, Device
from ifm3dpy.framegrabber import FrameGrabber, buffer_id

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")

try:
    import open3d

    OPEN3D_AVAILABLE = True
except ModuleNotFoundError:
    OPEN3D_AVAILABLE = False


def get_jpeg(self, img_queue: collections.deque):
    """Get the JPEG image from the frame
    and decodes it so it can be displayed.
    """
    rgb = cv2.imdecode(self.get_buffer(buffer_id.JPEG_IMAGE), cv2.IMREAD_UNCHANGED)
    img_queue.append(rgb)


def get_distance(self, img_queue: collections.deque):
    """Get the distance image from the frame
    and normalizes it for display.
    """
    img = cv2.normalize(
        self.get_buffer(buffer_id.RADIAL_DISTANCE_IMAGE),
        None,
        0,
        255,
        cv2.NORM_MINMAX,
        cv2.CV_8U,
    )
    img = cv2.applyColorMap(img, cv2.COLORMAP_JET)
    img_queue.append(img)


def get_amplitude(self, img_queue: collections.deque):
    """Returns the amplitude data extracted
    from the frame.
    """
    img_queue.append(self.get_buffer(buffer_id.NORM_AMPLITUDE_IMAGE))


def get_xyz(self, img_queue: collections.deque):
    """Returns the xyz data extracted
    from the frame.
    """
    img_queue.append(self.get_buffer(buffer_id.XYZ))


def display_2d(fg: FrameGrabber, getter: Callable, title: str):
    """Display the requested 2D data (distance, amplitude or JPEG)"""
    if getter.__name__ == "get_jpeg":
        fg.start([buffer_id.JPEG_IMAGE])
    else:
        fg.start(
            [
                buffer_id.NORM_AMPLITUDE_IMAGE,
                buffer_id.RADIAL_DISTANCE_IMAGE,
            ]
        )
    img_queue = collections.deque(maxlen=10)
    fg.on_new_frame(partial(getter, img_queue=img_queue))
    time.sleep(3)

    cv2.startWindowThread()
    cv2.namedWindow(title, cv2.WINDOW_NORMAL)
    while True:
        if img_queue:
            cv2.imshow(title, img_queue.pop())
            cv2.waitKey(15)

        if cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1:
            break

    cv2.destroyAllWindows()


def display_3d(fg: FrameGrabber, getter: Callable, title: str):
    """Stream and display the point cloud."""
    fg.start([buffer_id.XYZ])
    img_queue = collections.deque(maxlen=10)
    fg.on_new_frame(partial(getter, img_queue=img_queue))
    time.sleep(3)
    vis = open3d.visualization.Visualizer()
    vis.create_window(title)

    first = True
    while True:
        if img_queue:
            img = img_queue.pop()

            img = img.reshape(img.shape[0] * img.shape[1], 3)
            pcd = open3d.geometry.PointCloud()
            pcd.points = open3d.utility.Vector3dVector(img)

            vis.clear_geometries()
            vis.add_geometry(pcd, first)
            if not vis.poll_events():
                break

            vis.update_renderer()

            first = False

    vis.destroy_window()


def main():
    image_choices = ["distance", "amplitude", "jpeg"]
    if OPEN3D_AVAILABLE:
        image_choices += ["xyz"]

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--image",
        help="The image to received (default: distance). The jpeg image is only available for the O3R.",
        type=str,
        choices=image_choices,
        required=True,
    )
    parser.add_argument(
        "--ip",
        help="IP address of the sensor (default: 192.168.0.69)",
        type=str,
        required=False,
        default="192.168.0.69",
    )
    parser.add_argument(
        "--xmlrpc-port",
        help="XMLRPC port of the sensor (default: 80)",
        type=int,
        required=False,
        default=80,
    )
    parser.add_argument(
        "--port",
        help="The port from which images should be received (for the O3R only)",
        type=str,
        required=False,
    )
    args = parser.parse_args()

    getter = globals()["get_" + args.image]

    device = Device(args.ip, args.xmlrpc_port)
    device_type = device.who_am_i()
    logging.info(f"Device type is: {device_type}")
    if device_type == device.device_family.O3R:
        if args.port is None:
            raise ValueError("A port should be provided.")
        o3r = O3R(args.ip)
        fg = FrameGrabber(device, pcic_port=o3r.port(args.port).pcic_port)
        logging.info(f"Port: {args.port}")
    else:
        fg = FrameGrabber(device)
        if args.image == "jpeg":
            raise ValueError("JPEG images are only supported on the O3R platform.")

    title = f"{device_type} viewer"

    if args.image == "xyz":
        display_3d(fg, getter, title)
    else:
        display_2d(fg, getter, title)


if __name__ == "__main__":
    main()
