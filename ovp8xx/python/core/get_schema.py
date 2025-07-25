# -*- coding: utf-8 -*-
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

from ifm3dpy.device import O3R


def main(ip: str) -> None:
    o3r = O3R(ip)
    schema = o3r.get_schema()
    print("Displaying a sample of the JSON schema.")
    print("Schema for the network and fieldbus interfaces:")
    print(
        json.dumps(
            schema["properties"]["device"]["properties"]["network"]["properties"][
                "interfaces"
            ],
            indent=2,
        )
    )


if __name__ == "__main__":
    IP = "192.168.0.69"
    main(ip=IP)
