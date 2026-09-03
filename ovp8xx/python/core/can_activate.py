# -*- coding: utf-8 -*-
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# The CAN interface can only be activated with firmware
# versions 1.4.X or higher
from bootup_monitor import BootUpMonitor
from ifm3dpy.device import O3R


def _check_can_availability(o3r) -> None:
    if (
        "can0"
        in o3r.get(["/device/network/interfaces"])["device"]["network"]["interfaces"]
    ):
        # Get the can0 information: active status and bitrate
        can_info = o3r.get(["/device/network/interfaces/can0"])["device"]["network"][
            "interfaces"
        ]["can0"]
        return can_info
    else:
        raise RuntimeError("CAN interface not available in current firmware version.")


def main(ip: str) -> None:
    o3r = O3R(ip)
    can_info = _check_can_availability(o3r)
    if not can_info["active"]:
        print("activating can0 interface ...")
        o3r.set(
            {
                "device": {
                    "network": {
                        "interfaces": {
                            "can0": {
                                "active": True
                                # "bitrate": '125K' # here set the bitrate '250K', '500K' ...
                            }
                        }
                    }
                }
            }
        )
        print("Rebooting the device...")
        o3r.reboot()
        bootup_monitor = BootUpMonitor(o3r=o3r)
        if not bootup_monitor.wait_for_reboot():
            raise Exception("VPU not properly booted")

    can_info = o3r.get(["/device/network/interfaces/can0"])["device"]["network"][
        "interfaces"
    ]["can0"]
    if not can_info["active"]:
        raise RuntimeError("Activating the can0 interface failed.")
    else:
        print("The can0 interface is active!")


if __name__ == "__main__":
    IP = "192.168.0.69"
    print(f"Device IP: {IP}")
    main(IP)
