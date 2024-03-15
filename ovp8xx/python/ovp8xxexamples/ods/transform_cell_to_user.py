# %%##########################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

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

    ux = transform_matrix[0] * gx + transform_matrix[1] * gy + transform_matrix[2]
    uy = transform_matrix[3] * gx + transform_matrix[4] * gy + transform_matrix[5]

    return ux, uy


# %%


def main(ip, ods_cfg_file, calib_cfg_file):
    # %%
    # Necessary imports to run the full example.
    import logging
    logger = logging.getLogger(__name__)
    from ifm3dpy.device import O3R
    try: 
        from ovp8xxexamples.ods.ods_config import load_config_from_file, validate_json
        from ovp8xxexamples.ods.ods_stream import ODSStream
    except:
        try:
            from ods_config import load_config_from_file, validate_json
            from ods_stream import ODSStream
        except ImportError:
            raise ImportError("Unable to import the configuration and streaming functions: we cannot run this example without them.")

    o3r = O3R(ip)
    ################################################
    # Configure an app and start ODS data stream
    ################################################
    o3r.reset("/applications")
    schema = o3r.get_schema()

    o3r.set(validate_json(
        schema, load_config_from_file(calib_cfg_file)
    ))
    o3r.set(validate_json(
        schema, load_config_from_file(ods_cfg_file)
    ))
    # Expecting an application in "app0"
    o3r.set(
        validate_json(
            schema, {"applications": {"instances": {"app0": {"state": "RUN"}}}}
        )
    )
    # %%
    ods_stream = ODSStream(o3r=o3r, app_name="app0")
    ods_stream.start_ods_stream()
    ################################################
    # Get data and transform cell to user coordinates
    ################################################
    occupancy_grid = ods_stream.get_occupancy_grid()
    ux, uy = transform_cell_to_user(
        cells=occupancy_grid.image,
        transform_matrix=np.array(occupancy_grid.transform_cell_center_to_user),
    )
    logger.info(ux)
    logger.info(uy)
    # %%
    ods_stream.stop_ods_stream()


if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
        ODS_CFG_FILE = config.ODS_CFG_FILE
        CALIB_CFG_FILE = config.CALIB_CFG_FILE

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        ODS_CFG_FILE = "configs/ods_one_head_config.json"
        CALIB_CFG_FILE = "configs/extrinsic_one_head.json"

    main(ip=IP, ods_cfg_file=ODS_CFG_FILE, calib_cfg_file=CALIB_CFG_FILE)

# %%
