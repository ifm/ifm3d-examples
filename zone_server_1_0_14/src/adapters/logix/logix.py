#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import pycomm3
from bitstring import BitArray

import typing
import json
import logging
from pathlib import Path
import os

logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
)

# Tags that are written to the PLC
tag_signal = "ifm_o3r_vpu_signal"  # returns pycomm3.ULINT (64 bit)
tag_config = "ifm_o3r_zone_config"  # returns pycomm3.STRING
tag_zone_set_idx = "ifm_o3r_zone_idx"  # returns pycomm3.UDINT
tag_status_msg = "ifm_status_msg"

## process for setting up object TODO convert to adapter
# PLC_addr = config_json["compact-logix-addr"]  functionality into the actual logix handler
# plc = PLC(
#     PLC_addr, mock="", status_strings=USE_STRING_STATUS_UPDATE
# )
# plc.connect()
# plc.set_vpu_status("INIT")
# plc.write()

# Defining the signal message
# ... Several variables of info are included here so that we don't clutter the global scope of the customer's plc program
# ... This is all unpacked by the AOI to expose each of these values
specification_for_tags = {
    # note that the position of the bit or bit string in the signal tag is the offset
    tag_signal: {
        "heartbeat": {
            "offset": 0,
            "width": 1,
            "type": "BOOL",
            "desc": "counts upward",
            "default_value": BitArray("0b1"),
        },
        "status": {
            "offset": 1,
            "width": 8,
            "type": "USINT",
            "desc": "status code",
            "default_value": BitArray("0b00000000"),
        },
        "zone_1_occupancy": {
            "offset": 9,
            "width": 1,
            "type": "BOOL",
            "desc": "Whether or not zone is occupied",
            "default_value": BitArray("0b1"),
        },
        "zone_2_occupancy": {
            "offset": 10,
            "width": 1,
            "type": "BOOL",
            "desc": "Whether or not zone is occupied",
            "default_value": BitArray("0b1"),
        },
        "zone_3_occupancy": {
            "offset": 11,
            "width": 1,
            "type": "BOOL",
            "desc": "Whether or not zone is occupied",
            "default_value": BitArray("0b1"),
        },
    },
}


class Adapter:
    def __init__(self, address: str, mock="", status_strings=False) -> None:
        self.address = address
        self.connection_handle = None
        self.mock = mock

        self.tag_name = tag_signal
        self.data_tag_signal = specification_for_tags[tag_signal]
        for key, value in self.data_tag_signal.items():
            self.data_tag_signal[key]["value"] = value["default_value"]

        self.signal_sent_i = 0

        self.status_dict = {"ERR": 128, "INIT": 0, "RUN": 32, "IDLE": 33}
        self.status = "INIT"
        self.inv_status_dict = {v: k for k, v in self.status_dict.items()}

        self.mock_zone_idx_file = "mock_zone_idx.txt"
        self.cwd = Path(__file__).parent.parent
        if "r" in self.mock:
            if self.mock_zone_idx_file not in os.listdir(self.cwd):
                with open(self.cwd / self.mock_zone_idx_file, "w") as f:
                    f.write("1")

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def connect(self):
        """
        Opens a new connection.

        Closes existing connection if necessary.
        """
        if not ("r" in self.mock or "w" in self.mock):
            if self.connection_handle:
                return
            self.logger.debug("Connecting to PLC")
            self.connection_handle = pycomm3.LogixDriver(self.address)
            self.connection_handle.__enter__()

    def write(self):
        """writes vpu signal packet to plc"""
        self.signal_sent_i += 1
        self.logger.debug(f"Sent signal {self.signal_sent_i}")
        self.data_tag_signal["heartbeat"]["value"] = BitArray(
            f"0b{str(self.signal_sent_i%2)}"
        )
        if not "w" in self.mock:
            self.logger.debug("writing to PLC")
            self.connection_handle.write(
                tag_signal, self.package_tag(self.data_tag_signal)
            )
        else:
            self.logger.debug("mock-writing to PLC")
            tag_value = self.package_tag(self.data_tag_signal, verbose=True)
            pass

    def package_tag(
        self,
        specification: dict,
        n_bytes: int = 8,
        default: bool = False,
        verbose: bool = False,
    ) -> int:
        """
        Parses specification for signal to be sent to plc.

        Args:
            specification (dict): _description_
            n_bytes (int, optional): _description_. Defaults to 8.
            default (bool, optional): _description_. Defaults to False.
            verbose (bool, optional): _description_. Defaults to False.

        Returns:
            int: value that converts to signal to be read by plc
        """
        # write out big-endian signal
        signal = BitArray("0b" + "0" * 8 * n_bytes)
        for encoding in specification.values():
            if default:
                signal.overwrite(
                    encoding["default_value"][0 : encoding["width"]], encoding["offset"]
                )
            else:
                signal.overwrite(
                    encoding["value"][0 : encoding["width"]], encoding["offset"]
                )
        if verbose:
            self.logger.debug(f"Signal as binary (big-endian): {signal.b}")
        # return signal as little-endian
        encoded_signal = signal[::-1].uintbe
        if verbose:
            self.logger.debug(
                f"Default signal as unsigned int ready for transfer: {encoded_signal}"
            )
        return encoded_signal

    def set_vpu_status(self, message: typing.Union[int, str, Exception]):
        # handle error messages or search for
        message_str = str(message)
        if type(message) == int and 128 < message < 254:
            status = message
            self.status_code = status
        elif message_str in self.status_dict:
            status = self.status_dict[message_str]
        else:  # generic error
            status = 128
        status_bstring = BitArray("0b00000000")
        status_bstring.overwrite(BitArray(bin(status))[::-1], 0)
        self.data_tag_signal["status"]["value"] = status_bstring
        # set vpu status to str expression
        self.vpu_status = self.inv_status_dict[status]
        # logger.info(f"VPU")

    # def read_config_init(self) -> dict:
    #     ## Load config
    #     # config_str = self.conn.read(tag_config).value
    #     with open("conf.json", "r") as f:
    #         config = json.load(f)
    #         self.logger.info("using conf.json")
    #     # config = json.loads(config_str)
    #     return config

    def set_zones_occ(self, zone_occ: tuple):
        for zone_i, zone_i_occ in zip((1, 2, 3), zone_occ):
            self.data_tag_signal[f"zone_{zone_i}_occupancy"]["value"] = BitArray(
                f"0b{zone_i_occ}"
            )
        self.logger.info(
            f"Zones (set-{self.zone_set_idx}) -> (G-{zone_occ[2]})(Y-{zone_occ[1]})(R-{zone_occ[0]})"
        )

    def read_zone_idx(self) -> int:
        self.zone_set_idx = self.connection_handle.read(tag_zone_set_idx).value
        return self.zone_set_idx

    def report_error_code(self, code=0):
        """
        attempt an error report to plc

        Generic error is 0

        Args:
            code (int, optional): code up to 64 to report to plc. Defaults to 0.
        """
        self.set_vpu_status(code)
        self.write()

    def report_issue(self, code: int = 0, status_desc=None):
        "generic error: 128, other errors: 129-254"
        self.set_vpu_status(code)
        self.status = status_desc
        self.status_code = code
        self.write()


# %%
