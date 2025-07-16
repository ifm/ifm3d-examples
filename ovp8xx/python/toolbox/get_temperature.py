# -*- coding: utf-8 -*-
#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
"""_summary_
This examples shows how to retrieve the internal
temperature values from the O3R platform, for
the VPU, the IMU and any connected camera.

:raises RuntimeError: If overtemperature is reached.
"""
import logging
from datetime import datetime

from ifm3dpy import O3R

logger = logging.getLogger(__name__)


def main(ip: str):
    dt_string = datetime.now().strftime("%Y_%m_%d-%H_%M_%S")
    logging.basicConfig(
        filename=f"temperature_test_{dt_string}.log",
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    logger.info(f"IP: {ip}")

    o3r = O3R(ip=ip)
    temperatures = o3r.get(["/device/diagnostic/temperatures"])["device"]["diagnostic"][
        "temperatures"
    ]
    logger.info(f"{temperatures}")

    for e in temperatures:
        # test for tuple: ('overtemperature', True)
        if ("overtemperature", True) in list(e.items()):
            logger.warning(f"overtemperature reached: {e}")
            raise RuntimeWarning(f"overtemperature reached: {e}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
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
