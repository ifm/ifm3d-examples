# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This example showcases how to visualize ODS
# ODS data.
#############################################
import collections
import json
import logging
from time import perf_counter
from typing import Any, Callable, Deque

import cv2
import matplotlib.pyplot as plt
import numpy as np
from ifm3dpy.deserialize import ODSInfoV1, ODSOccupancyGridV1, ODSPolarOccupancyGridV1
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import Frame, FrameGrabber, buffer_id


class ODSVisualizer:
    def __init__(
        self, o3r: str, app: str, queue_length: int, timeout: int, window_name: str
    ):
        self.o3r = o3r
        self.window_name = window_name
        self.window_created = False
        self.keypress = -1
        self.count = 0
        self.update_pause = 0
        self.timeout = timeout
        self.app = app
        self.queues = {
            "occupancy_grid": collections.deque(maxlen=queue_length),
            "ods_info": collections.deque(maxlen=queue_length),
            "polar_occupancy_grid": collections.deque(maxlen=queue_length),
        }
        self.fg = FrameGrabber(self.o3r, self.o3r.port(app).pcic_port)
        self.zone_coordinates = None

    def add_frame(self, frame: Frame) -> None:
        """Add a received frame to the appropriate queue."""
        if frame.has_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID):
            self.queues["occupancy_grid"].append(
                frame.get_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID)
            )
        if frame.has_buffer(buffer_id.O3R_ODS_INFO):
            self.queues["ods_info"].append(frame.get_buffer(buffer_id.O3R_ODS_INFO))
            self.zone_coordinates = self.o3r.get(
                [
                    "/applications/instances/"
                    + self.app
                    + "/configuration/zones/zoneCoordinates"
                ]
            )["applications"]["instances"][self.app]["configuration"]["zones"][
                "zoneCoordinates"
            ]
        if frame.has_buffer(buffer_id.O3R_ODS_POLAR_OCC_GRID):
            self.queues["polar_occupancy_grid"].append(
                frame.get_buffer(buffer_id.O3R_ODS_POLAR_OCC_GRID)
            )

    def get_data(self, queue: Deque, deserializer: Callable) -> Any:
        """Retrieve deserialized data from the queue."""
        start = perf_counter()
        while (perf_counter() - start) * 1000 <= self.timeout:
            if queue:
                return deserializer().deserialize(queue.pop())
        raise TimeoutError("Timeout waiting for data")

    def open_window(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        self.window_created = True

    def update_image(self, image: np.ndarray = np.zeros((100, 100, 3), np.uint8)):
        keypress = -1
        if self.window_created:
            if image is not None:
                cv2.imshow(self.window_name, image)
                keypress = cv2.waitKey(1)
        else:
            raise Exception("Window not created yet. Call open_window() first")
        self.keypress = keypress
        if self.keypress != -1:
            if self.keypress in [27, ord("q")]:  # 'esc' or 'q'
                self.window_created = False
                self.destroy_window()

    def destroy_window(self):
        try:
            cv2.destroyWindow(self.window_name)
        except Exception as err:
            if "578" in str(err) or "window_w32.cpp:1261" in str(err):
                pass
            else:
                raise err
        self.window_created = False

    def draw_text(
        self,
        img,
        *,
        text,
        uv_top_left,
        color=(255, 255, 255),
        fontScale=1,
        thickness=1,
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        outline_color=(0, 0, 0),
        line_spacing=1.5,
    ):
        assert isinstance(text, str)
        uv_top_left = np.array(uv_top_left, dtype=float)
        assert uv_top_left.shape == (2,)
        for line in text.splitlines():
            (w, h), _ = cv2.getTextSize(
                text=line, fontFace=fontFace, fontScale=fontScale, thickness=thickness
            )
            uv_bottom_left_i = uv_top_left + [0, h]
            org = tuple(uv_bottom_left_i.astype(int))
            if outline_color is not None:
                cv2.putText(
                    img,
                    text=line,
                    org=org,
                    fontFace=fontFace,
                    fontScale=fontScale,
                    color=outline_color,
                    thickness=thickness * 3,
                    lineType=cv2.LINE_AA,
                )
            cv2.putText(
                img,
                text=line,
                org=org,
                fontFace=fontFace,
                fontScale=fontScale,
                color=color,
                thickness=thickness,
                lineType=cv2.LINE_AA,
            )
            uv_top_left += [0, h * line_spacing]

    def render_visual(
        self, raw_occupancy_grid: ODSOccupancyGridV1, zones_occupied, upscale_factor=5
    ):
        self.count += 1

        # Access the image attribute of the ODSOccupancyGridV1 object
        occupancy_grid = raw_occupancy_grid.image
        # Increase contrast in visualization:
        occupancy_grid = occupancy_grid - 51
        # Allow visualization to be colorful
        occupancy_grid = cv2.cvtColor(occupancy_grid, cv2.COLOR_GRAY2BGR)
        # Make visualization higher resolution. Use no interpolation.
        occupancy_grid = cv2.resize(
            occupancy_grid,
            np.array(occupancy_grid.shape[:2]) * upscale_factor,
            interpolation=0,
        )
        # Add gridlines 1m apart
        for offset in range(-5, 5):
            occupancy_grid[(100 + offset * 20) * upscale_factor, :] += 50
            occupancy_grid[:, (100 + offset * 20) * upscale_factor] += 50

        # Paint zones on visualization
        colors = (
            ((0, 0, 150), (0, 0, 255)),
            ((0, 150, 150), (0, 255, 255)),
            ((0, 150, 0), (0, 255, 0)),
        )
        for zone, zone_occupied, color in list(
            zip(
                self.zone_coordinates,
                zones_occupied,
                colors,
            )
        )[::-1]:
            contour = [
                np.array((np.array(zone) * 20 + 100) * upscale_factor, dtype=np.int32)
            ]
            mask = np.zeros_like(occupancy_grid)
            cv2.drawContours(mask, contour, -1, np.array(color[zone_occupied]) / 5, -1)
            occupancy_grid = np.uint8(
                np.minimum(
                    np.uint16(occupancy_grid) + mask, np.ones_like(occupancy_grid) * 255
                )
            )
            occupancy_grid = cv2.drawContours(
                occupancy_grid, contour, 0, color[zone_occupied], 1
            )

        # Rotate and flip occupancy grid to feel right for desktop testing
        occupancy_grid = cv2.rotate((occupancy_grid), cv2.ROTATE_90_COUNTERCLOCKWISE)
        occupancy_grid = cv2.flip((occupancy_grid), 1)

        # Add text overlays
        text_lines = ["Zones: " + str(zones_occupied)]
        text = "\n".join(text_lines)
        self.draw_text(img=occupancy_grid, text=text, uv_top_left=(10, 10))

        return occupancy_grid

    def render_polar_visual(self, polar_occupancy_grid: ODSPolarOccupancyGridV1):
        # Convert distances from mm to meters
        distances = np.array(polar_occupancy_grid.polarOccGrid) / 1000.0
        distances[distances == 65.535] = np.nan  # Mask out "no occupied cell" values
        angles = np.linspace(0, 2 * np.pi, num=len(distances), endpoint=False)
        # Rotate the plot by 90 degrees to be aligned with the occupancy grid
        angles = angles + (np.pi / 2)

        # Check if the plot already exists
        if not hasattr(self, "polar_fig"):
            # Create the plot if it doesn't exist
            self.polar_fig, self.polar_ax = plt.subplots(
                subplot_kw={"projection": "polar"}
            )
            self.polar_scatter = self.polar_ax.scatter(
                angles, distances, s=5, color="r", label="Occupied Cells"
            )
            self.polar_ax.set_title(f"Polar Occupancy Grid - Frame: {self.count}")
            self.polar_ax.legend()
        else:
            # Update the existing plot
            self.polar_scatter.set_offsets(np.c_[angles, distances])
            self.polar_ax.set_title(f"Polar Occupancy Grid - Frame: {self.count}")

        # Refresh the plot
        plt.draw()
        plt.pause(0.001)

        # Keep the plot open and responsive
        if not plt.fignum_exists(self.polar_fig.number):
            self.polar_fig, self.polar_ax = plt.subplots(
                subplot_kw={"projection": "polar"}
            )
            self.polar_scatter = self.polar_ax.scatter(
                angles, distances, s=5, color="r", label="Occupied Cells"
            )
            self.polar_ax.set_title(f"Polar Occupancy Grid - Frame: {self.count}")
            self.polar_ax.legend()


def async_diagnostic_callback(message: str, app_instance: str) -> None:
    """
    Callback to handle diagnostic messages and monitor the status of a specific application.

    Args:
        message (str): Diagnostic message in JSON format.
        app_instance (str): Name of the application instance to monitor (e.g., "app0").
    """
    diagnostic = json.loads(message)
    groups = diagnostic.get("groups", {})
    app_status = groups.get(app_instance, "unknown")
    print(f"\nNew Diagnostic: The status of application '{app_instance}': {app_status}")
    if app_status == "critical":
        print(
            f"⚠️ Application '{app_instance}' is in a critical state! Stop the Robot!!"
        )


def main(ip, app_instance):
    # Initialize O3R device
    logger = logging.getLogger(__name__)
    logging.basicConfig()
    logger.setLevel(logging.INFO)
    # create O3R device
    o3r = O3R(ip)

    # Start diagnostic monitoring with a separate FrameGrabber
    diag_fg = FrameGrabber(o3r, 50009)
    diag_fg.on_async_error(
        callback=lambda id, message: async_diagnostic_callback(message, app_instance)
    )
    print(
        "Starting async diagnostic monitoring. \nErrors ids and descriptions will be logged."
    )
    diag_fg.start([])

    # Display data
    visualizer = ODSVisualizer(
        o3r,
        app_instance,
        queue_length=5,
        timeout=700,
        window_name="ODS output - Occupancy grid, zones and diagnostic. Press 'q' to exit.",
    )
    visualizer.open_window()
    visualizer.fg.start(
        [
            buffer_id.O3R_ODS_OCCUPANCY_GRID,
            buffer_id.O3R_ODS_INFO,
            buffer_id.O3R_ODS_POLAR_OCC_GRID,
        ]
    )
    visualizer.fg.on_new_frame(lambda frame: visualizer.add_frame(frame))

    try:
        while visualizer.window_created:
            # Collect ODS output
            raw_occupancy_grid = visualizer.get_data(
                visualizer.queues["occupancy_grid"], ODSOccupancyGridV1
            )
            zones = visualizer.get_data(
                visualizer.queues["ods_info"], ODSInfoV1
            ).zone_occupied
            polar_occupancy_grid = visualizer.get_data(
                visualizer.queues["polar_occupancy_grid"], ODSPolarOccupancyGridV1
            )

            # Generate a pretty visual
            ods_visualization = visualizer.render_visual(raw_occupancy_grid, zones)
            visualizer.update_image(ods_visualization)

            # Generate polar visual
            visualizer.render_polar_visual(polar_occupancy_grid)

    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received. Exiting...")
        visualizer.destroy_window()
    except Exception as e:
        logger.info("Viewing interrupted, turning off viewer.")
        visualizer.destroy_window()
        raise e


if __name__ == "__main__":
    IP = "192.168.0.69"
    app_instance = "app0"
    main(ip=IP, app_instance=app_instance)
