#############################################
# Copyright 2024-present ifm electronic, gmbh
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
import subprocess
import shlex
import threading
import traceback

import canopen
import semver

import ifm3dpy
import ifm3dpy.device

try:
    from ovp_docker_utils import oem_logging
except ImportError:
    oem_logging = None

from utils.http_api import Backend

logger = logging.getLogger("oem")


class PeriodicMessage:
    def __init__(self, nw: canopen.Network, cobid, data, interval, logger, verbose=True):
        self.interval = interval
        self.thread = None
        self.is_running = False
        self._data = data
        self.cobid = cobid
        self.logger = logger
        self.nw = nw
        self.verbose = verbose

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, value):
        self._data = value

    def start(self):
        if self.is_running:
            return

        self.is_running = True
        self.thread = threading.Thread(target=self.send)
        self.thread.start()

    def stop(self):
        self.is_running = False

    def send(self):
        messaging_start_t = time.perf_counter()
        i = 0
        while self.is_running:
            if (time.perf_counter() - messaging_start_t) % self.interval > i:
                try:
                    send_start_t = time.perf_counter()
                    self.nw.send_message(self.cobid, self.data)
                    sent_t = time.perf_counter() - send_start_t
                    if self.verbose:
                        self.logger.info(f"send_t = {sent_t}")
                except Exception as e:
                    if "Transmit buffer full" in str(e):
                        self.logger.info("transmit buffer full")
                    else:
                        raise e
                if self.interval - sent_t > 0.001:
                    time.sleep(self.interval-sent_t)
            else:
                time.sleep(.005)
            ...
class MsgDB:
    def __init__(self):
        self.db = {}
        self.cnt = 0

    def log_msg(self, COBID, message, timestamp):
        rt = time.perf_counter()
        
        # if COBID in self.db:
        #     self.db[COBID] = {"last_100_times":[],"last_message_t":rt}
        # else:
        #     self.db[COBID]["last_100_times"].insert(0,rt-self.db[COBID]["last_message_t"])
        #     self.db[COBID]["last_100_times"]=self.db[COBID]["last_100_times"][:100]
        #     self.db[COBID]["last_message_t"]=rt

        formatted_string = ' '.join([format(byte, '02x') for byte in message])
        msg = {'ID':format(COBID,'03x'),"data":formatted_string,"t":timestamp}
        logger.info(f"Recvd -> {msg}")

        if self.cnt%20==0:
            logger.info(f"longest period between last {COBID} msg: {round(max(self.db[COBID]['last_100_times']),4)}")
        self.cnt+=1

def main():
    try:
        on_vpu = os.environ.get("ON_VPU", "0") in ["1", "True", "y"]

        log_dir_name = "logs"
        log_series_name = "Demos"

        config_file = Path(__file__).parent /"config.json"
        with open(config_file, "r") as f:
            config = json.load(f)

        ts_format = "%y.%m.%d_%H.%M.%S%z"
        now = datetime.now().astimezone()
        now_local_ts = now.strftime(ts_format)

        backend = Backend(port = config["port"])

        msg = "Running CAN interface from a docker container!"

        total_cached_log_size = config["total_cached_log_size"]

        # If running in docker, check that the system clock is synchronized
        VPU_address_on_vpu = "172.17.0.1"
        o3r = ifm3dpy.device.O3R(VPU_address_on_vpu)
        try:
            clock_is_synced = o3r.get(
            )["device"]["clock"]["sntp"]["systemClockSynchronized"]
        except:
            clock_is_synced = False
        # If the clock is not synced, the log file name will just be the next highest integer
        if not clock_is_synced:
            now_local_ts = None


        log_path = oem_logging.setup_log_handler(
            logger,
            total_cached_log_size=total_cached_log_size,
            log_dir=str(Path(__file__).parent / log_dir_name),
            log_series_name=log_series_name,
            t_initialized=now_local_ts,)
        

        # setup canopen
        bitrate = 125000
        managed_id = "0x64"
        channel = "can0"
        bustype = "socketcan"
        heartbeat_time_ms =100
        ods_framerate = 1
        autostart_pdos = False

        fw_version = ".".join(o3r.get()["device"]["swVersion"]["firmware"].split("-")[0].split(".")[:3])  # get the first 3 parts of the version number
        logger.info(f"Device firmware version: {fw_version}")

        # Check for firmware compatibility
        if any([(semver.compare(fw_version, range[0]) >= 0 and semver.compare(range[1], fw_version) >= 0) for range in [["1.0.0", "1.2.50"]]]):
            commands_to_set_baud_rate = [
                "ip link set can0 down",
                f"ip link set can0 type can bitrate {bitrate}",
                "ip link set can0 up",
            ]
            for command in commands_to_set_baud_rate:
                logger.info(f"running command: {command}")
                start = time.perf_counter()
                with subprocess.Popen(
                    shlex.split(command),
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                ) as process:
                    buffer = ""
                    while time.perf_counter() < start+0.5:
                        output = process.stdout.readline()
                        if output == '' and process.poll() is not None:
                            break
                        if output:
                            buffer += output
                            logger.info(">>> "+output.strip().decode())
        elif semver.compare(fw_version, "1.4.0") >= 0:
            logger.info("Firmware version is 1.4.0 or later, no need to set baud rate via command line")
            # o3r.set(...)
        else:
            time.sleep(4)
            logger.error(f"Firmware version {fw_version} not supported")
            sys.exit(1)


        managed_id = int(managed_id, 16)
        nw = canopen.Network()
        vpu_node = canopen.LocalNode(managed_id, object_dictionary=None)
        nw.add_node(vpu_node, object_dictionary=None)
        nw.connect(channel=channel, bustype=bustype, bitrate=bitrate)

        heartbeat_time_ms = heartbeat_time_ms
        # self.vpu_node.nmt.update_heartbeat()
        ...
        initialized_heartbeat = False
        initialized_tpdo = False
        pdo_task = PeriodicMessage(
            nw,
            0x180 + managed_id,
            b"\x00" * 8,
            1 / ods_framerate,
            logger,
        )
        heartbeat = PeriodicMessage(
            nw,
            0x700 + managed_id,
            b"\x00",
            heartbeat_time_ms / 1000,
            logger,
        )

        if autostart_pdos:
            vpu_node.nmt._state = 5
            pdo_task.start()

        heartbeat.start()
        
        msg_db = MsgDB()

        for x in range(0x780):
            nw.subscribe(x, msg_db.log_msg)

    except Exception as e:
        time.sleep(4)
        logger.error("Failed to initialize: " + str(e) + "\n" + traceback.format_exc())
        sys.exit(1)

    # Drop a test artifact into the corresponding log directory
    log_artifact_path = log_path.replace(".log", "_vpu_config_dump.json")
    try:
        VPU_base_config = o3r.get()
        with open(log_artifact_path, "w") as f:
            json.dump(VPU_base_config, indent=4, fp=f)
    except Exception as e:
        logger.error("Failed to cache vpu config: " + str(e))
        with open(log_artifact_path, "w") as f:
            f.write("")

    try:
        while True:
            logger.info(msg)
            backend.update_state()
            backend.backend_state = backend.front_end_state
            print("Backend state: ", backend.backend_state)
            time.sleep(2)

            if on_vpu:
                # print any recent can messages recieved
                ...

    except KeyboardInterrupt:
        print("Exiting...")
        sys.exit(0)


if __name__ == "__main__":
    main()

# %%
