#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from time import sleep
import logging
from logging.handlers import RotatingFileHandler
import os
from pathlib import Path
from datetime import datetime


def setup_log_handler(logger, total_cached_log_size=1e8, log_dir_name="logs"):
    # Configure rotating log file handler
    try:
        if total_cached_log_size > 0:
            cache_logs = True

        if cache_logs:
            # set up logging to file
            log_dir = Path(__file__).absolute().parent.parent / log_dir_name

            if not log_dir.exists():
                os.mkdir(log_dir)
                most_recent_log = 0
            else:
                logs = os.listdir(log_dir)

                total_size = 0
                most_recent_log = 0
                for log in logs[
                    ::-1
                ]:  # reverse order so that the last log is the first checked for size
                    if log[:3] != "log" or log[-4:] != ".txt":
                        continue
                    i = int(log.replace("log", "").replace(".txt", ""))
                    if i > most_recent_log:
                        most_recent_log = i
                    total_size += os.path.getsize(log_dir / log)

                    if total_size > total_cached_log_size:
                        os.remove(log_dir / log)

            ts = datetime.now().strftime("%Y-%m-%dT%H.%M.%S")
            log_i = most_recent_log + 1
            log_fname = f"log{log_i}.txt"

            log_path = log_dir / log_fname
            formatter = logging.Formatter(
                "%(asctime)s:%(filename)-10s:%(levelname)-8s:%(lineno)d:%(message)s"
            )
            my_handler = RotatingFileHandler(
                log_path,
                mode="a",
                maxBytes=total_cached_log_size,
                backupCount=0,
                encoding=None,
                delay=0,
            )
            my_handler.setFormatter(formatter)
            my_handler.setLevel(logging.INFO)
            logger.addHandler(my_handler)

    except Exception as e:
        sleep(10e8)
