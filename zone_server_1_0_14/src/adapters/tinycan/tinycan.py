#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################


import logging
import time
import json
from pathlib import Path
import threading

from ..data_models import ZoneSet

import sys

sys.path.append("../../..")
from rotating_logger import setup_log_handler

import canopen


CAN_SPECIFIC_ODS_STATE_CODE = {"IDLE": 0, "CONF": 1, "RUN": 2, "ERROR": 3}

SDO_COMMANDS = {0x22: 0x42, 0x23: 0x43, 0x27: 0x47, 0x2B: 0x4B, 0x2F: 0x4F, 0x40: 0x60}

NMT_STATES = {
    0: "INITIALISING",
    4: "STOPPED",
    5: "OPERATIONAL",
    80: "SLEEP",
    96: "STANDBY",
    127: "PRE-OPERATIONAL",
}

import threading
import time


class PeriodicMessage:
    def __init__(self, nw: canopen.Network, cobid, data, interval, logger):
        self.interval = interval
        self.thread = None
        self.is_running = False
        self._data = data
        self.cobid = cobid
        self.logger = logger
        self.nw = nw

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
                    self.logger.info(f"send_t = {sent_t}")
                    if self.interval - sent_t > 0.001:
                        time.sleep(self.interval-sent_t)
                except Exception as e:
                    if "Transmit buffer full" in str(e):
                        self.logger.info("transmit buffer full")
                    else:
                        raise e
            else:
                time.sleep(.005)
            ...


class Adapter:
    def set_vpu_status(self, status):
        self.ods_state_to_send["odsMode"] = status

    def set_zones_occ(self, occupancy):
        self.ods_state_to_send["occupancy"] = occupancy

    def set_zones(self, zone_set):
        self.ods_state_to_send["zones"] = zone_set

    def recv(self):
        return self.ods_state_recieved["zones"] 

    def push(self):
        self.pdo_task.data = self.serialize_state_to_send()

        if not self.initialized_tpdo:
            if self.vpu_node.nmt._state == 5:
                self.pdo_task.start()
                self.initialized_tpdo == True
        elif self.vpu_node.nmt._state != 5:
            self.pdo_task.stop()
            self.initialized_tpdo = False
        if not self.initialized_heartbeat:
            if self.vpu_node.nmt._state >0:
                self.heartbeat.start()
                self.initialized_heartbeat == True
        elif self.vpu_node.nmt._state==0:
            self.heartbeat.stop()
            self.initialized_heartbeat = False

    def send_data_to_manager_node(self):
        self.cnt += 1
        data = self.serialize_state_to_send()
        try:
            self.nw.send_message(0x180 + self.managed_id, data)
        except Exception as e:
            if "Transmit buffer full" in str(e):
                self.logger.info("transmit buffer full")
            else:
                raise e

    def serialize_state_to_send(self):
        data = b""
        if not isinstance(self.ods_state_to_send["zones"], ZoneSet):
            data += b"\xFF\xFF"
        else:
            data += self.ods_state_to_send["zones"].index.to_bytes(
                2, byteorder="little"
            )
        data += CAN_SPECIFIC_ODS_STATE_CODE[self.ods_state_to_send["odsMode"]].to_bytes(
            2, byteorder="little"
        )
        occupancy_int = 0
        for i, zone in enumerate(self.ods_state_to_send["occupancy"]):
            occupancy_int += zone * 2**i
        data += occupancy_int.to_bytes(2, byteorder="little")
        return data

    def __init__(
        self,
        log_level="info",
        managed_id=0x64,
        ods_framerate=20,
        channel="can0",
        bustype="socketcan",
        bitrate=125000,
        sync_offset_ms=-1,
        heartbeat_time_ms=1000,
        autostart_pdos=0,
        **kwargs,
    ):
        logging.basicConfig(
            format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
            datefmt="%y-%m-%d %H:%M:%S",
            level={
                "spew": logging.DEBUG,
                "info": logging.INFO,
                "debug": logging.DEBUG,
            }[log_level],
        )
        self.logger = logging.getLogger(__name__)

        managed_id = int(managed_id, 16)
        self.managed_id = managed_id

        self.nw = canopen.Network()
        self.vpu_node = canopen.LocalNode(managed_id, object_dictionary=None)
        self.nw.add_node(self.vpu_node, object_dictionary=None)
        self.nw.connect(channel=channel, bustype=bustype, bitrate=bitrate)

        self.heartbeat_time_ms = heartbeat_time_ms
        # self.vpu_node.nmt.update_heartbeat()
        ...
        self.initialized_heartbeat = False
        self.initialized_tpdo = False
        self.pdo_task = PeriodicMessage(
            self.nw,
            0x180 + self.managed_id,
            b"\x00" * 8,
            1 / ods_framerate,
            self.logger,
        )
        self.heartbeat = PeriodicMessage(
            self.nw,
            0x700 + self.managed_id,
            self.vpu_node.nmt._state,
            1 / ods_framerate,
            self.logger,
        )

        if autostart_pdos:
            self.vpu_node.nmt._state = 5

        self.ods_framerate = ods_framerate

        self.sync_offset_ms = sync_offset_ms
        self.sync_init = None

        self.ods_state_to_send = {
            "odsMode": "IDLE",
            "occupancy": [1, 1, 1],
            "zones": ZoneSet(index=0),
        }
        self.ods_state_recieved = {"zones": ZoneSet(index=0)}
        self.cnt = 0

        # scan for all messages
        if log_level == "spew":
            for x in range(0x700):
                self.nw.subscribe(x, self.log_incoming_message)
            setup_log_handler(self.logger, 10e8, log_dir_name="can_logs")

        # subscribe to each message in specification
        # tpdo
        self.nw.subscribe(self.managed_id + 0x200, self.handle_zone_update)
        # sync
        self.nw.subscribe(0x80, self.handle_sync)
        # nmt
        self.nw.subscribe(0x0, self.vpu_node.nmt.on_command)
        # nmt
        self.nw.subscribe(0x0, self.nmt_reset)
        # SDO serving
        self.nw.subscribe(0x600 + managed_id, self.handle_sdo)

    def nmt_reset(self, COBID, message, timestamp):
        ...

    def handle_sdo(self, COBID, message, timestamp):
        # None of these sdo commands influence behavior.
        send_start_t = (
            time.perf_counter()
        )
        if message == b"\x40\x00\x10\x00\x00\x00\x00\x00":
            response = b"\x43\x00\x10\x00\x64\x00\x00\x00"
            self.nw.send_message(0x580 + self.managed_id, response)
        else:
            command_code = message[0]
            if command_code in SDO_COMMANDS:
                self.log_incoming_message(COBID, message, timestamp)
                response = SDO_COMMANDS[command_code].to_bytes(1, "big") + message[1:]
                self.nw.send_message(0x580 + self.managed_id, response)
        sent_t = (
            time.perf_counter() - send_start_t
        )
        self.logger.info(
            f"=================={sent_t}"
        )

    def handle_sync(self, COBID, message, timestamp):
        sync_init = time.perf_counter()
        if self.sync_offset_ms > 0:
            sync_init += self.sync_offset_ms / 1000
        self.sync_init = sync_init
        # self.log_incoming_message(COBID,message,timestamp)

    def handle_zone_update(self, COBID, message, timestamp):
        self.vpu_node.nmt.state = "OPERATIONAL"
        self.ods_state_recieved["zones"] = ZoneSet(
            index=int.from_bytes(message[:2], byteorder="little")
        )
        if self.ods_state_recieved["zones"].index == 0:
            self.vpu_node.nmt.state == "PRE-OPERATIONAL"
        else:
            self.vpu_node.nmt.state == "OPERATIONAL"
        # self.log_incoming_message(COBID,message,timestamp)

    def log_incoming_message(self, COBID, message, timestamp):
        formatted_string = " ".join([format(byte, "02x") for byte in message])
        msg = {"ID": format(COBID, "03x"), "data": formatted_string}  # ,"t":timestamp}
        self.logger.debug(f"Recvd -> {msg}")


if __name__ == "__main__":
    config_dir = Path(__file__).parent.parent.parent.parent / "config"
    try:
        with open(config_dir / "which_config", "r") as f:
            which_config = f.read().strip()
    except:
        which_config = "configs/config.json"

    with open(config_dir.parent / which_config, "r") as f:
        config_json = json.load(f)

    print(config_json)
    adapter_config = [
        adapter for adapter in config_json["adapters"] if adapter["type"] == "tinycan"
    ][0]
    adapter = Adapter(**adapter_config["params"])

    ods_framerate = adapter_config["params"]["ods_framerate"]

    while True:
        time.sleep(1 / ods_framerate)
        adapter.set_vpu_status("RUN")
        adapter.set_zones_occ((0, 1, 1))
        adapter.set_zones(ZoneSet(index=3))
        adapter.push()
