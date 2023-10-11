#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from ifm3dpy import O3R, FrameGrabber, buffer_id

from ods_queue import ODSDataQueue
from zone_server_config import ZoneServerConfig

import logging
from time import perf_counter

logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
)


class ODSStream:
    def __init__(
        self,
        o3r: O3R,
        app_name: str,
        buffer_length=1,
        stream_zones=True,
        stream_occupancy_grid=True,
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
        self.SCHEMA = {
            "layouter": "flexible",
            "format": {"dataencoding": "ascii"},
            "elements": [
                {"type": "string", "value": "star", "id": "start_string"},
                {"type": "blob", "id": "O3R_ODS_OCCUPANCY_GRID"},
                {"type": "blob", "id": "O3R_ODS_INFO"},
                {"type": "string", "value": "stop", "id": "end_string"},
            ],
        }
        # self.plc = plc
        self.logger = logging.getLogger(__name__)
        self.logger.debug("Initialized ODS Stream")

    def start_ods_stream(self) -> None:
        self.logger.debug("Starting framegrabber")
        self.ods_fg.start(self.buffer_ids, self.SCHEMA)
        self.logger.debug("Started framegrabber")
        self.ods_fg.on_new_frame(self.ods_data_queue.add_frame)

    def stop_ods_stream(self) -> None:
        self.ods_fg.stop()

    def get_zone_occupancy(self, ODS_data_collection_timeout) -> list:
        start = perf_counter()
        while True:
            if len(self.ods_data_queue._ods_info_queue):
                zone_occupied = self.ods_data_queue.zone_occupied
                break
            elif perf_counter() - start > ODS_data_collection_timeout:
                raise TimeoutError("Timeout waiting for zone data")
        return zone_occupied

    def poll_for_data(self):
        return len(self.ods_data_queue._occupancy_grid_queue)

    def get_zones_and_occupancy_data(self):
        # collect zone occupancy data
        zones_occupied = self.ods_data_queue.zone_occupied
        # collect occupancy grid
        raw_occupancy_grid = self.ods_data_queue.occupancy_grid
        return zones_occupied, raw_occupancy_grid
