# -*- coding: utf-8 -*-
# %%##########################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import numpy as np


def transform_cell_to_user(cells: np.ndarray, transform_matrix: np.ndarray):
    """transform the cell coordinates to cartesian map coordinates:
    transform[0, 0] * zone_0_x + transform[0, 1] * zone_0_y + transform[0, 2]

    Args:
        cells (np.ndarray): occupancy grid image (occupancy_grid.image)
        transform_matrix (np.ndarray): matrix containing the transformation parameters (occupancy_grid.transform_cell_center_to_user)

    Returns:
        tuple: cartesian map coordinates corresponding to the coordinates
                of the edge of the cell in X and Y directions.
    """
    gy, gx = np.indices(cells.shape)

    ux = transform_matrix[0] * gx + transform_matrix[1] * gy + transform_matrix[2]
    uy = transform_matrix[3] * gx + transform_matrix[4] * gy + transform_matrix[5]

    return ux, uy
