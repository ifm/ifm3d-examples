#!/usr/bin/env python3
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This example shows how to get the JSON schema
# corresponding to the current configuration of
# the device.
# The schema can be used to validate the configuration
# and provides details like data type, default, min, and max values for
# each parameter.

import json
import logging
from ifm3dpy.device import O3R

logger = logging.getLogger(__name__)


def main(ip: str) -> None:
    o3r = O3R(ip)
    schema = o3r.get_schema()
    logger.info("Displaying a sample of the JSON schema.")
    logger.info("Schema for the network and fieldbus interfaces:")
    logger.info(
        json.dumps(
            schema["properties"]["device"]["properties"]["network"]["properties"][
                "interfaces"
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
    except ImportError:
        # Otherwise, use default values
        logger.warning(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        logger.warning("Defaulting to the default configuration.")
        IP = "192.168.0.69"

    main(ip=IP)
