#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This example showcases how to start the ODS
# data stream and add the received frame to a
# queue using ifm3dpy.
#############################################
# %%
import logging
from time import perf_counter, sleep

import numpy as np
from ifm3dpy import O3R, FrameGrabber, buffer_id

from ods_queue import ODSDataQueue


logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
)


class ODSStream:
    """Provides functions showcasing how to receive data from the O3R platform."""

    def __init__(
        self,
        o3r: O3R,
        app_name: str = "app0",
        stream_zones=True,
        stream_occupancy_grid=True,
        buffer_length=5,
        timeout=500,
    ) -> None:
        self.ods_data_queue = ODSDataQueue(buffer_length=buffer_length)

        self.buffer_ids = []
        if stream_zones:
            self.buffer_ids.append(buffer_id.O3R_ODS_INFO)
        if stream_occupancy_grid:
            self.buffer_ids.append(buffer_id.O3R_ODS_OCCUPANCY_GRID)

        self.ods_fg = FrameGrabber(
            o3r,
            o3r.get([f"/applications/instances/{app_name}/data/pcicTCPPort"])[
                "applications"
            ]["instances"][app_name]["data"]["pcicTCPPort"],
        )

        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.logger.debug("Initialized ODS Stream")

    def start_ods_stream(self) -> None:
        """Start the data stream and register a callback
        to add received frames to a queue."""
        self.logger.info("Starting framegrabber")
        self.ods_fg.start(self.buffer_ids)
        self.logger.debug("Waiting 1 second after framegrabber start")
        sleep(1)
        self.ods_fg.on_new_frame(self.ods_data_queue.add_frame)

    def stop_ods_stream(self) -> None:
        self.ods_fg.stop()

    def get_zones(self) -> list:
        """
        Retrieve deserialized data from the queue.

        :raises TimeoutError: if no data is received within specified timeout.
        :return: the zones info
        """
        start = perf_counter() * 100
        while perf_counter() * 100 - start <= self.timeout:
            if len(self.ods_data_queue.ods_info_queue):
                return self.ods_data_queue.zones
        msg = "Timeout waiting for zone data"
        self.logger.exception(msg)
        raise TimeoutError(msg)

    def get_occupancy_grid(self) -> np.ndarray:
        """
        Retrieve deserialized data from the queue.
        return: the occupancy grid data
        raises: a timeout if no data is received within specified timeout.
        """
        start = perf_counter() * 100
        while perf_counter() * 100 - start <= self.timeout:
            self.logger.debug("Waiting for occupcancy grid data")
            if len(self.ods_data_queue.occupancy_grid_queue):
                return self.ods_data_queue.occupancy_grid
        msg = "Timeout waiting for occupancy grid data"
        self.logger.exception(msg)
        raise TimeoutError(msg)


def main():
    IP = "192.168.0.69"
    o3r = O3R(IP)

    ###################################
    # Performing a reset to make sure
    # we start with an empty configuration
    ###################################
    o3r.reset("/applications")
    # Instantiating the ODSStream object.
    # We are expecting an app in app0.
    # This will fail as no ODS application exists on the device.
    try:
        ods_stream = ODSStream(
            o3r, "app0", stream_zones=True, stream_occupancy_grid=True, timeout=500
        )
    # Failing silently to continue with the example
    except Exception:
        pass

    ###################################
    # Configure an ODS application for
    # the example. Assume 3D port in
    # port 2. Change the config file if
    # needed.
    ###################################
    from ods_config import load_config_from_file, validate_json

    # Assuming a camera facing forward, label up,
    # 60 cm above the floor.
    # We keep the extrinsic calibration and the ODS configuration
    # separate for clarity. You can keep all configurations
    # in one file if necessary.
    schema = o3r.get_schema()
    config_snippet = validate_json(
        schema, load_config_from_file("configs/extrinsic_one_head.json"))
    o3r.set(config_snippet)
    config_snippet = validate_json(
        schema, load_config_from_file("configs/ods_one_head_config.json"))
    o3r.set(config_snippet)
    # We did not start the application when configuring it,
    # so we need to start it now (change state to "RUN")
    config_snippet = (
        {"applications": {"instances": {"app0": {"state": "RUN"}}}})
    o3r.set(config_snippet)

    ###################################
    # Start streaming ODS data and get
    # zone and occupancy grid output
    # Expect an app in "app0".
    ###################################
    ods_stream = ODSStream(o3r, "app0", stream_zones=True,
                           stream_occupancy_grid=True)
    ods_stream.start_ods_stream()

    zones = ods_stream.get_zones()
    ods_stream.logger.info(f"Current zone id used: {zones.zone_config_id}")
    ods_stream.logger.info(f"Zones occupancy: {zones.zone_occupied}")
    ods_stream.logger.info(f"Zones info timestamp: {zones.timestamp_ns}")

    occupancy_grid = ods_stream.get_occupancy_grid()
    ods_stream.logger.info(
        f"Occupancy grid (first row): {occupancy_grid.image[0]}")
    ods_stream.logger.info(
        f"Occupancy grid timestamp: {occupancy_grid.timestamp_ns}")
    ods_stream.logger.info(
        f"Center of cell to user transformation matrix: {occupancy_grid.transform_cell_center_to_user}"
    )

    ods_stream.stop_ods_stream()
    ods_stream.logger.info("You reached the end of the ODSStream tutorial!")


if __name__ == "__main__":
    main()

# %%
