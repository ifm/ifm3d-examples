#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from dataclasses import dataclass
import numpy as np


@dataclass
class Position:
    start: int
    stop: int


class Parse_ODS_info:
    TIMESTAMP_POSITION = Position(0, 8)
    ZONE_OCCUPIED = Position(8, 11)
    ZONE_CONFIG_ID = Position(11, 15)

    def __init__(self, chunk: np.ndarray):
        self._timestamp_ns = np.frombuffer(
            chunk[0][: Parse_ODS_info.TIMESTAMP_POSITION.stop],
            dtype="<Q",
        )[0]

        self._zoneOccupied = np.frombuffer(
            chunk[0][
                Parse_ODS_info.ZONE_OCCUPIED.start : Parse_ODS_info.ZONE_OCCUPIED.stop
            ],
            dtype="<B",
        )

        self._zoneConfigID = np.frombuffer(
            chunk[0][
                Parse_ODS_info.ZONE_CONFIG_ID.start : Parse_ODS_info.ZONE_CONFIG_ID.stop
            ],
            dtype="<I",
        )[0]

    @property
    def timestamp(self) -> int:
        return self._timestamp_ns

    @property
    def zone_occupied(self) -> np.ndarray:
        return self._zoneOccupied

    @property
    def zone_config_id(self) -> int:
        return self._zoneConfigID


class Parse_ODS_occupancy_grid:
    TIMESTAMP_POSITION = Position(0, 8)
    WIDTH_POSITION = Position(8, 12)
    HEIGHT_POSITION = Position(12, 16)
    TRANSFORM_POSITION = Position(16, 40)
    OCCUPANCY_GRID_POSITION = Position(40, -1)

    def __init__(self, chunk: np.ndarray):
        self._timestamp_ns = np.frombuffer(
            chunk[0][: Parse_ODS_occupancy_grid.TIMESTAMP_POSITION.stop],
            dtype="<Q",
        )[0]

        self._width = np.frombuffer(
            chunk[0][
                Parse_ODS_occupancy_grid.WIDTH_POSITION.start : Parse_ODS_occupancy_grid.WIDTH_POSITION.stop
            ],
            dtype="<I",
        )[0]

        self._height = np.frombuffer(
            chunk[0][
                Parse_ODS_occupancy_grid.HEIGHT_POSITION.start : Parse_ODS_occupancy_grid.HEIGHT_POSITION.stop
            ],
            dtype="<I",
        )[0]

        self._transform = np.frombuffer(
            chunk[0][
                Parse_ODS_occupancy_grid.TRANSFORM_POSITION.start : Parse_ODS_occupancy_grid.TRANSFORM_POSITION.stop
            ],
            dtype="<6f",
        ).reshape(2, 3)

        image = np.frombuffer(
            chunk[0][Parse_ODS_occupancy_grid.OCCUPANCY_GRID_POSITION.start :],
            dtype=f"<{self._width*self._height}B",
        )
        self._image = image.reshape(self._width, self._height)

    @property
    def timestamp(self) -> int:
        return self._timestamp_ns

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    @property
    def occupancy_grid(self) -> np.ndarray:
        return self._image

    @property
    def transform_cell_center_to_user(self) -> np.ndarray:
        return self._transform
