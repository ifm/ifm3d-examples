#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%#########################################
# Some boilerplate for tidy logging within a
# docker container on the o3r camera system.
#############################################


import logging
import time
import os
import sys
import json
from pathlib import Path
from datetime import datetime

import ifm3dpy

# from o3r_docker_manager import oem_logging
import oem_logging

logger = logging.getLogger("oem")

def main():
    in_docker = os.environ.get("IN_DOCKER", "0") in ["1", "True", "y"]

    log_dir_name = "logs"
    log_series_name = "Demos"

    config_file = Path(__file__).parent / "configs"/"config.json"
    with open(config_file, "r") as f:
        config = json.load(f)

    ts_format = "%y.%m.%d_%H.%M.%S%z"
    now = datetime.now().astimezone()
    now_local_ts = now.strftime(ts_format)

    msg = "Running example script oem_logging.py"
    if in_docker:
        msg += " from a docker container!"

        total_cached_log_size = config["total_cached_log_size"]

        # If running in docker, check that the system clock is synchronized
        VPU_address_in_docker = "127.17.0.1"
        o3r = ifm3dpy.O3R(VPU_address_in_docker)
        try:
            clock_is_synced = o3r.get(
            )["device"]["clock"]["sntp"]["systemClockSynchronized"]
        except:
            clock_is_synced = False
        # If the clock is not synced, the log file name will just be the next highest integer
        if not clock_is_synced:
            now_local_ts = None
    else:
        o3r = ifm3dpy.O3R(config["VPU_address_for_deployment"])
        msg += " from a local machine!"
        total_cached_log_size = 1e10  # 10 GB on a local machine

    log_path = oem_logging.setup_log_handler(
        logger,
        total_cached_log_size=total_cached_log_size,
        log_dir=str(Path(__file__).parent / log_dir_name),
        log_series_name=log_series_name,
        t_initialized=now_local_ts,)

    # Drop a test artifact into the corresponding log directory
    log_artifact_path = log_path.replace(".log", "_vpu_config_dump.json")
    try:
        with open(log_artifact_path, "w") as f:
            json.dump(o3r.get(), indent=4, fp=f)
    except Exception as e:
        logger.error("Failed to cache vpu config: " + str(e))
        with open(log_artifact_path, "w") as f:
            f.write("")

    try:
        while True:
            time.sleep(2)
            logger.info("Logged message: " + msg)
            print("Stdout printed message: " + msg, flush=True)

    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()

# %%
