# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This example showcases how to start the ODS
# data stream and add the received frame to a
# queue using ifm3dpy.
#############################################
import collections
import json
from time import perf_counter, sleep
from typing import Any, Callable, Deque

from ifm3dpy.deserialize import (
    ODSExtrinsicCalibrationCorrectionV1,
    ODSInfoV1,
    ODSOccupancyGridV1,
    ODSPolarOccupancyGridV1,
)
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import Frame, FrameGrabber, buffer_id


def async_diagnostic_callback(message: str, app_name: str) -> None:
    """
    Callback to handle diagnostic messages and monitor the status of a specific application.

    Args:
        message (str): Diagnostic message in JSON format.
        app_name (str): Name of the application to monitor (e.g., "app0").
    """
    diagnostic = json.loads(message)
    groups = diagnostic.get("groups", {})
    app_status = groups.get(app_name, "unknown")
    print(f"\nNew Diagnostic: The status of application '{app_name}': {app_status}")
    if app_status == "critical":
        print(f"⚠️ Application '{app_name}' is in a critical state! Stop the Robot!!")


class ODSStream:
    def __init__(self, o3r: O3R, app: str, queue_length: int, timeout: int):
        self.o3r = o3r
        self.timeout = timeout
        self.app = app  # Store the application name
        self.queues = {
            "occupancy_grid": collections.deque(maxlen=queue_length),
            "ods_info": collections.deque(maxlen=queue_length),
            "polar_occupancy_grid": collections.deque(maxlen=queue_length),
            "ods_extrinsic_calibration_correction": collections.deque(
                maxlen=queue_length
            ),
        }
        self.fg = FrameGrabber(self.o3r, self.o3r.port(app).pcic_port)

    def add_frame(self, frame: Frame) -> None:
        """Add a received frame to the appropriate queue."""
        if frame.has_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID):
            self.queues["occupancy_grid"].append(
                frame.get_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID)
            )
        if frame.has_buffer(buffer_id.O3R_ODS_INFO):
            self.queues["ods_info"].append(frame.get_buffer(buffer_id.O3R_ODS_INFO))
        if frame.has_buffer(buffer_id.O3R_ODS_POLAR_OCC_GRID):
            self.queues["polar_occupancy_grid"].append(
                frame.get_buffer(buffer_id.O3R_ODS_POLAR_OCC_GRID)
            )
        if frame.has_buffer(buffer_id.O3R_ODS_EXTRINSIC_CALIBRATION_CORRECTION):
            self.queues["ods_extrinsic_calibration_correction"].append(
                frame.get_buffer(buffer_id.O3R_ODS_EXTRINSIC_CALIBRATION_CORRECTION)
            )

    def get_data(self, queue: Deque, deserializer: Callable) -> Any:
        """Retrieve deserialized data from the queue."""
        start = perf_counter()
        while (perf_counter() - start) * 1000 <= self.timeout:
            if queue:
                return deserializer().deserialize(queue.pop())
        raise TimeoutError("Timeout waiting for data")

    def start_streaming(self):
        """Start the ODS data stream."""
        self.fg.on_new_frame(lambda frame: self.add_frame(frame))
        self.fg.start(
            [
                buffer_id.O3R_ODS_INFO,
                buffer_id.O3R_ODS_OCCUPANCY_GRID,
                buffer_id.O3R_ODS_POLAR_OCC_GRID,
                buffer_id.O3R_ODS_EXTRINSIC_CALIBRATION_CORRECTION,
            ]
        )

    def stop_streaming(self):
        """Stop the ODS data stream and diagnostics."""
        self.fg.stop()


def print_ods_data(ods_stream: ODSStream) -> None:
    """Print ODS data from the queues."""
    try:
        # ODS zones data
        print("-------------ODS zones data --------------------------")
        zones = ods_stream.get_data(ods_stream.queues["ods_info"], ODSInfoV1)
        print(f"Current zone id used: {zones.zone_config_id}")
        print(f"Zones occupancy: {zones.zone_occupied}")
        print(f"Zones info timestamp: {zones.timestamp_ns}")

        # ODS occupancy grid data
        print("--------------ODS occupancy grid data------------------")
        occupancy_grid = ods_stream.get_data(
            ods_stream.queues["occupancy_grid"], ODSOccupancyGridV1
        )
        print(f"Occupancy grid image shape: {occupancy_grid.image.shape}")
        print(f"Occupancy grid timestamp: {occupancy_grid.timestamp_ns}")
        print(
            f"Center of cell to user transformation matrix: {occupancy_grid.transform_cell_center_to_user}"
        )

        # ODS polar occupancy grid data
        print("--------------ODS polar occupancy grid data ----------")
        polar_occupancy_grid = ods_stream.get_data(
            ods_stream.queues["polar_occupancy_grid"], ODSPolarOccupancyGridV1
        )
        # distances are in mm, the 360° are divided into 675 values
        distance_0degree = polar_occupancy_grid.polarOccGrid[0] / 1000
        if (
            distance_0degree == 65.535
        ):  # 65.535 is a special value for no object detected
            print("No object detected at 0° using the Polar occupancy grid")
        else:
            print(
                f"Distance to the first object at 0° using the Polar occupancy grid: {distance_0degree} m"
            )

        # ODS extrinsic calibration correction data
        print("--------------ODS extrinsic calibration correction data ----------")
        extrinsic_calibration_correction = ods_stream.get_data(
            ods_stream.queues["ods_extrinsic_calibration_correction"],
            ODSExtrinsicCalibrationCorrectionV1,
        )
        # rot_delta_valid is  Array of [X, Y, Z]. A flag indicating a valid estimation of rotation delta value (0: invalid, 1: valid)
        print(f"rot_delta_valid: {extrinsic_calibration_correction.rot_delta_valid}")

        # rot_head_to_user is Array of rotation value [rad] of the (corrected) extrinsic calibration (extrinsicHeadToUser). Array of [X, Y, Z].
        print(f"rot_head_to_user: {extrinsic_calibration_correction.rot_head_to_user}")

    except TimeoutError as e:
        print(e)


def main(ip: str, app: str, queue_length: int, timeout: int) -> None:
    o3r = O3R(ip)
    ods_stream = ODSStream(o3r, app, queue_length, timeout)
    ods_stream.start_streaming()

    # Start diagnostic monitoring
    diag_fg = FrameGrabber(o3r, 50009)
    diag_fg.on_async_error(
        callback=lambda id, message: async_diagnostic_callback(message, app)
    )
    print("Starting async diagnostic monitoring.")
    diag_fg.start([])

    try:
        while True:
            print_ods_data(ods_stream)
            sleep(1)  # Adjust the sleep time as needed

    except KeyboardInterrupt:
        print("Stopping the ODS data streaming tutorial.")
        ods_stream.stop_streaming()
        diag_fg.stop()


if __name__ == "__main__":
    IP = "192.168.0.69"
    APP = "app0"
    queue_length = 5
    timeout_ms = 300
    main(ip=IP, app=APP, queue_length=queue_length, timeout=timeout_ms)
