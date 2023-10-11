#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from ods_parse import Parse_ODS_info, Parse_ODS_occupancy_grid
import numpy as np
import collections
import logging
from ifm3dpy import buffer_id

logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
)


class ODSDataQueue:
    def __init__(self, buffer_length: int) -> None:
        self._buffer_length = buffer_length
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.ERROR)
        self._occupancy_grid_queue = collections.deque(maxlen=self._buffer_length)
        self._ods_info_queue = collections.deque(maxlen=self._buffer_length)

    def add_frame(self, frame) -> None:
        self.logger.debug("Adding frame if available")
        if frame.has_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID):
            self._occupancy_grid_queue.append(
                frame.get_buffer(buffer_id.O3R_ODS_OCCUPANCY_GRID)
            )
            self.logger.debug("Added occ grid")
        if frame.has_buffer(buffer_id.O3R_ODS_INFO):
            self._ods_info_queue.append(frame.get_buffer(buffer_id.O3R_ODS_INFO))
            self.logger.debug("Added zone")

    # @property
    # def timestamp(self) -> float:
    #     self.logger.debug("Pop(ed) image from ring buffer and return timestamp")
    #     return Parse_ODS_occupancy_grid(self._occupancy_grid_queue.pop()).timestamp

    @property
    def occupancy_grid(self) -> np.ndarray:
        self.logger.debug("About to pop occupancy grid")
        return Parse_ODS_occupancy_grid(self._occupancy_grid_queue.pop()).occupancy_grid

    @property
    def zone_occupied(self) -> np.ndarray:
        self.logger.debug("About to pop zone occupied")
        return Parse_ODS_info(self._ods_info_queue.pop()).zone_occupied

    @property
    def zone_config_id(self) -> int:
        self.logger.debug("About to pop zone config id")
        return Parse_ODS_info(self._ods_info_queue.pop()).zone_config_id
