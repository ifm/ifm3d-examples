# %%##########################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import os

import numpy as np


def transform_cell_to_user(cells: np.ndarray, transform_matrix: np.ndarray):
    """transform the cell coordinates to cartesian map coordinates:
    transform[0, 0] * zone_0_x + transform[0, 1] * zone_0_y + transform[0, 2]

    Args:
        cells (np.ndarray): occupancy grid image
        transform_matrix (np.ndarray): matrix containing the transformation parameters

    Returns:
        tuple: cartesian map coordinates corresponding to the coordinates 
                of the edge of the cell in X and Y directions.
    """
    gy, gx = np.indices(cells.shape)

    ux = (
        transform_matrix[0] * gx
        + transform_matrix[1] * gy
        + transform_matrix[2]
    )
    uy = (
        transform_matrix[3] * gx
        + transform_matrix[4] * gy
        + transform_matrix[5]
    )

    return ux, uy
# %%


def main():
    # %%
    import logging
    logger = logging.getLogger(__name__)
    # %%################################################
    # Getting IP address and instantiating O3R object
    ################################################
    ADDR = os.environ.get("IFM3D_IP", "192.168.0.69")
    logger.info(f"Device IP: {ADDR}")
    from ifm3dpy.device import O3R
    o3r = O3R(ADDR)
    ################################################
    # Configure an app and start ODS data stream
    ################################################
    from ods_config import load_config_from_file, validate_json
    from ods_stream import ODSStream
    o3r.reset("/applications")
    schema = o3r.get_schema()

    config_snippet_extrinsics = validate_json(
        schema, load_config_from_file("configs/ods_one_head_config.json"))
    o3r.set(config_snippet_extrinsics)
    # Expecting an application in "app0"
    o3r.set(validate_json(schema, {"applications": {
            "instances": {"app0": {"state": "RUN"}}}}))
    # %%
    ods_stream = ODSStream(o3r=o3r, app_name="app0")
    ods_stream.start_ods_stream()
    ################################################
    # Get data and transform cell to user coordinates
    ################################################
    occupancy_grid = ods_stream.get_occupancy_grid()
    ux, uy = transform_cell_to_user(
        cells=occupancy_grid.image,
        transform_matrix=np.array(occupancy_grid.transform_cell_center_to_user))
    logger.info(ux)
    logger.info(uy)
    # %%


if __name__ == "__main__":
    main()

# %%
