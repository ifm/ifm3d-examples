#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import collections
import logging
import numpy as np
from ifm3dpy.framegrabber import buffer_id
from ifm3dpy.deserialize import ODSInfoV1, ODSOccupancyGridV1

logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
)


class ODSDataQueue:
    """This class provides facilities to handle data queues in an ODS application."""

    def __init__(self, buffer_length: int) -> None:
        self._buffer_length = buffer_length
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        self.occupancy_grid_queue = collections.deque(
            maxlen=self._buffer_length)
        self.ods_info_queue = collections.deque(maxlen=self._buffer_length)

    def add_frame(self, frame) -> None:
        """Add a received frame to a queue.
        We use two separate queues for the occupancy grid and the zone info."""
        self.logger.debug("Adding frame if available")
        if frame.has_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID):
            self.occupancy_grid_queue.append(
                frame.get_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID)
            )
            self.logger.debug("Added occ grid")
        if frame.has_buffer(buffer_id.O3R_ODS_INFO):
            self.ods_info_queue.append(
                frame.get_buffer(buffer_id.O3R_ODS_INFO))
            self.logger.debug("Added zone")

    @property
    def occupancy_grid(self):
        """
        Returns: the deserialized occupancy grid data, which contains the width,
        height, image (the occupancy grid), timestamp and transform_cell_center_to_user matrix.
        """
        self.logger.debug("About to pop occupancy grid")
        return ODSOccupancyGridV1().deserialize(self.occupancy_grid_queue.pop())

    @property
    def zones(self):
        """
        Returns: the deserialized zone data, which contains the timestamp,
        zone_config_id and zone_occupied."""
        self.logger.debug("About to pop zone occupied")
        return ODSInfoV1().deserialize(self.ods_info_queue.pop())
