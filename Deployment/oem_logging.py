#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import logging
import time
import os
import sys
import json
from logging.handlers import RotatingFileHandler
from pathlib import Path
from datetime import datetime

import ifm3dpy

LOG_FORMAT = "%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s"
logging.basicConfig(
    format=LOG_FORMAT,
    datefmt="%y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    level=logging.INFO,
)
logger = logging.getLogger("root")


def setup_log_handler(logger, total_cached_log_size:int=1e8, log_dir_name:str="logs", log_series_name:str="Demos", t_initialized=None)->str:
    """
    Sets up a rotating log handler for the specified logger. If the total_cached_log_size is exceeded, the oldest log files will be deleted first. The log files will be stored in the specified log_dir_name/log_series_name directory. The log file name will be the next highest integer in the log_series_name directory, unless t_initialized is specified, in which case the log file name will be the specified t_initialized timestamp.

    Parameters
    ----------
    logger : logging.Logger
        The logger to which the rotating log handler will be added
    total_cached_log_size : int, optional
        Number of bytes to limit the specified log directory to, by default 1e8
    log_dir_name : str, optional
        Where to find/manage logs can be absolute or relative, by default "logs"
    log_series_name : str, optional
        A title for the application or test series, by default "demo"
    t_initialized : str, optional
        Timestamp of the test run, by default None

    Returns
    -------
    str
        the path to the log file
    """


    cache_logs = total_cached_log_size > 0
    if cache_logs:
        # Set up logging to file
        if log_dir_name[:2] == "..":
            log_dir = Path(__file__).absolute(
            ).parent.parent / log_dir_name[3:]
        elif Path(log_dir_name).is_absolute():
            log_dir = Path(log_dir_name)
        else:
            log_dir = Path(__file__).absolute().parent / log_dir_name

        # Setup log directory
        if not log_dir.exists():
            os.mkdir(log_dir)
        else:
            # Check for oldest log files to delete them first if necessary
            log_files = []
            for root, dirs, files in os.walk(log_dir):
                for file in files:
                    path = os.path.join(root, file)
                    log_files.append({"path": path, "fname": file, "size": os.path.getsize(
                        path), "last_modified": os.path.getmtime(path)})
            log_files = sorted(log_files, key=lambda k: k['last_modified'])
            total_size = 0
            for log_file in log_files:
                total_size += log_file["size"]
                if total_size > total_cached_log_size:
                    os.remove(log_file["path"])

        # Setup log-series directory
        # Run identifier could be the next int in a series or the specified t_initialized
        log_series_dir = log_dir / log_series_name
        if not log_series_dir.exists():
            os.mkdir(log_series_dir)
            most_recent_log = 0
        else:
            log_entries = os.listdir(log_series_dir)
            if t_initialized is None:
                most_recent_log = 0
                for log_entry in log_entries:
                    if log_entry[-4:] == ".log":
                        run_identification = log_entry.replace(".log", "")
                        if run_identification.isnumeric():
                            i = int(run_identification)
                            if i > most_recent_log:
                                most_recent_log = i
        if t_initialized is None:
            this_run_identifier = str(most_recent_log + 1)
        else:
            this_run_identifier = str(t_initialized)

        log_fname = this_run_identifier + ".log"
        log_path = log_series_dir / log_fname

        rotating_handler = RotatingFileHandler(
            log_path,
            mode="a",
            maxBytes=total_cached_log_size,
            backupCount=0,
            encoding=None,
            delay=0,
        )
        rotating_handler.setFormatter(logging.Formatter(LOG_FORMAT))
        rotating_handler.setLevel(logging.INFO)
        logger.addHandler(rotating_handler)
        return str(log_path)


if __name__ == "__main__":

    log_dir_name = "logs"
    log_series_name = "Demos"
    config_file = Path(__file__).parent / "configs"/"config.json"

    with open(config_file, "r") as f:
        config = json.load(f)

    ts_format = "%y.%m.%d_%H.%M.%S%z"
    now = datetime.now().astimezone()
    now_local_ts = now.strftime(ts_format)

    in_docker = os.environ.get("IN_DOCKER", "0") in ["1", "True", "y"]
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
        total_cached_log_size = 1e10 # 10 GB on a local machine
    
    log_path = setup_log_handler(
        logger,
        total_cached_log_size=total_cached_log_size,
        log_dir_name=log_dir_name,
        log_series_name=log_series_name,
        t_initialized=now_local_ts,)

    # Drop a test artifact into the corresponding log directory
    log_artifact_path = log_path.replace(".log", "_vpu_config_dump.json")
    try:
        with open(log_artifact_path, "w") as f:
            json.dump(o3r.get(),indent=4,fp=f)
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
#%%


