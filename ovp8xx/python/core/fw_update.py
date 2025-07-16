# -*- coding: utf-8 -*-
################################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
################################################
# This examples shows how to update the firmware
# of an O3R device.
################################################

from os import path

from ifm3dpy.device import O3R
from ifm3dpy.swupdater import SWUpdater

###################################
# Configure the IP and the path to
# the firmware file on your system
###################################
IP = "192.168.0.69"
FILENAME = "/path/to/o3r/fw/OVP81x_Firmware_1.20.29.6418.swu"
o3r = O3R(IP)
swu = SWUpdater(o3r)

if not path.exists(FILENAME):
    raise ValueError("Provided swu file does not exist")

try:
    print("Rebooting to recovery mode...")
    swu.reboot_to_recovery()
    swu.wait_for_recovery()
    if swu.flash_firmware(swu_file=FILENAME, timeout_millis=1800):
        swu.wait_for_productive()
        print("Update successful. System ready!")
    else:
        raise TimeoutError("Timeout during firmware update")
except RuntimeError:
    raise RuntimeError("Firmware update failed!")

print("Current firmware version: ")
print(o3r.get(["/device/swVersion/firmware"]))
