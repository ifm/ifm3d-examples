# -*- coding: utf-8 -*-
################################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
################################################
# EDUCATIONAL EXAMPLE ONLY - NOT FOR PRODUCTION
#
# This basic firmware update script is intended for learning purposes.
# For production use, run fw_update.py in this directory, which:
#   - Automatically detects OVP80x versus OVP81x hardware
#   - Handles edge cases and firmware transition requirements
#   - Provides comprehensive error recovery and logging
#   - Avoids getting stuck in recovery or mixed-version scenarios
#
# This simplified script may fail in scenarios such as:
#   - 0.16.x ↔ 1.x.x firmware transitions
#   - Devices already in or requiring recovery mode
#   - Hardware-specific update requirements for OVP81x variants
################################################

from os import path

from ifm3dpy.device import O3R
from ifm3dpy.swupdater import SWUpdater


###################################
# Configure the IP and the path to
# the firmware file on your system
###################################
def main(ip: str, firmware_file: str) -> None:

    o3r = O3R(ip)
    swu = SWUpdater(o3r)

    if not path.exists(firmware_file):
        raise ValueError("Provided swu file does not exist")

    try:
        print("Rebooting to recovery mode...")
        swu.reboot_to_recovery()
        swu.wait_for_recovery()
        if swu.flash_firmware(swu_file=firmware_file, timeout_millis=1800):
            swu.wait_for_productive()
            print("Update successful. System ready!")
        else:
            raise TimeoutError("Timeout during firmware update")
    except RuntimeError:
        raise RuntimeError("Firmware update failed!")

    print("Current firmware version: ")
    print(o3r.get(["/device/swVersion/firmware"]))


if __name__ == "__main__":
    IP = "192.168.0.69"
    FIRMWARE_FILE = "/path/to/o3r/fw/OVP81x_xxxx.swu"
    main(ip=IP, firmware_file=FIRMWARE_FILE)
