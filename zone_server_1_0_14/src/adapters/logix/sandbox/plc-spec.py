#%%
# this file is a bit of an introduction to the pycomm3 module and the initial plan to implement with ods

# requires installation of:
import pycomm3
from bitstring import BitArray
import bitstring as bs

# builtins
import json
import time
from pprint import pprint

#%%

###############################################################################
###########################################################
# tags that are read from PLC
tag_config = "ifm_o3r_zone_config"  # returns pycomm3.STRING
tag_zone_set_idx = "ifm_o3r_zone_idx"  # returns pycomm3.UDINT

######################################
# configuration example:
example_zone_set = [
    [[0, 1], [1, 1], [1, -1], [0, -1]],
    [[1, 1], [2, 1], [2, -1], [1, -1]],
    [[2, 1], [3, 1], [3, -1], [2, -1]],
]
zone_config = {
    "config_id": "id1",
    "init_json": {},
    "zones": {1: example_zone_set}
    # TODO write a schema to validate json
}
#####################################
# Demo of reading configuration from device
# (pycomm3 delivers a python string that will need to be loaded as json)
zone_config_python_utf8_as_read_from_plc = json.dumps(zone_config)

zone_config_python_dict = json.loads(zone_config_python_utf8_as_read_from_plc)
pprint(zone_config_python_dict)

#%%
###########################################################
# Tags that are written to the PLC
tag_signal = "ifm_o3r_vpu_signal"  # returns pycomm3.ULINT (128 bit)

#%%
###############################################
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
            "default_value": BitArray("0b01111110"),
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


def get_tag_signal(specification: dict, default=False, verbose=False) -> int:

    # write out big-endian signal
    signal = BitArray("0b" + "0" * 64)
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
        print(f"Default signal as binary (big-endian): {signal.b}")
    # return signal as little-endian
    encoded_signal = signal[::-1].uintbe
    if verbose:
        print(f"Default signal as unsigned int ready for transfer: {encoded_signal}")
    return encoded_signal


default_signal = get_tag_signal(
    specification_for_tags[tag_signal], default=True, verbose=True
)
#%%

# initialize a tag_signal data dictionary using the default values
data_tag_signal = specification_for_tags[tag_signal]
for key, value in data_tag_signal.items():
    data_tag_signal[key]["value"] = value["default_value"]

#%%
# Example of reading and writing the necessary tags
plc_addr = "192.168.1.62"
attempts = 1000

for attempt in range(attempts):
    time.sleep(0.04)
    try:
        # with pycomm3.LogixDriver(plc_addr) as plc:
        plc = pycomm3.LogixDriver(plc_addr)
        plc.__enter__()
        if True:

            # alternate_heartbeat_signal
            data_tag_signal["heartbeat"]["value"] = BitArray(f"0b{str(attempt%2)}")
            pprint(plc.read(tag_config))
            plc.write(tag_signal, get_tag_signal(data_tag_signal))
            pprint(plc.read(tag_zone_set_idx))
            # break
    except pycomm3.CommError as e:
        print(
            f"Could not connect to plc at {plc_addr} - {attempt+1} of {attempts} attempts"
        )
        continue
    except pycomm3.ResponseError as e:
        print(
            f"Could not recieve response from plc at {plc_addr} - {attempt+1} of {attempts} attempts"
        )
        continue


# %%
