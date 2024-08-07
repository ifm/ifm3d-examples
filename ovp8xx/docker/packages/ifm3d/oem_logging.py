#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s"
logging.basicConfig(
    format=LOG_FORMAT,
    datefmt="%y-%m-%d %H:%M:%S",
    stream=sys.stdout,
    level=logging.INFO,
)
logger = logging.getLogger("oem")


def setup_log_handler(
    logger: logging.Logger = logger,
    total_cached_log_size: int = -1,
    log_dir: str = "~/ovp8xx_logs",
    log_series_name: str = "Demos",
    t_initialized=None,
    format=LOG_FORMAT,
    level=logging.INFO,
) -> str:
    """
    Sets up a rotating log handler for the specified logger. NOTE to prevent data loss, be careful when using this tool for local development. If the total_cached_log_size is exceeded, the oldest files in the specified log_dir_name/log_series_name directory will be deleted first. The log files will be stored in the specified log_dir_name/log_series_name directory. The log file name will be the next highest integer in the log_series_name directory, unless t_initialized is specified, in which case the log file name will be the specified t_initialized timestamp.

    Parameters
    ----------
    logger : logging.Logger
        The logger to which the rotating log handler will be added
    total_cached_log_size : int, optional
        Number of bytes to limit the specified log directory to. 0 is no log file and no pruning will occur, -1 is unlimited and no pruning will occur, by default 1e8
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

    log_path = None
    if total_cached_log_size != 0:
        # Set up logging to file
        if log_dir[:2] == "..":
            log_dir = Path(os.getcwd()).parent / log_dir[3:]
        if log_dir[:1] == "~":
            log_dir = Path.home() / log_dir[2:]
        elif Path(log_dir).is_absolute():
            log_dir = Path(log_dir)
        else:
            log_dir = Path(os.getcwd()) / log_dir

        # Setup log directory
        if not log_dir.exists():
            os.mkdir(log_dir)

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

            if total_cached_log_size > 0:
                # Check for oldest log files to delete them first if necessary
                log_files = []
                for root, dirs, files in os.walk(log_series_dir):
                    for file in files:
                        path = os.path.join(root, file)
                        log_files.append(
                            {
                                "path": path,
                                "fname": file,
                                "size": os.path.getsize(path),
                                "last_modified": os.path.getmtime(path),
                            }
                        )
                log_files = sorted(log_files, key=lambda k: k["fname"])
                total_size = 0
                for log_file in log_files:
                    total_size += log_file["size"]
                    if total_size > total_cached_log_size:
                        os.remove(log_file["path"])

        if t_initialized is None:
            this_run_identifier = str(most_recent_log + 1)
        else:
            this_run_identifier = str(t_initialized)

        log_fname = this_run_identifier + ".log"
        log_path = log_series_dir / log_fname

        if total_cached_log_size < 0:
            total_cached_log_size = 0
        rotating_handler = RotatingFileHandler(
            log_path,
            mode="a",
            maxBytes=total_cached_log_size,
            backupCount=0,
            encoding=None,
            delay=0,
        )
        rotating_handler.setFormatter(logging.Formatter(format))
        rotating_handler.setLevel(level)
        logger.addHandler(rotating_handler)

    return str(log_path)
