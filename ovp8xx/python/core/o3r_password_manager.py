# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import os

from bootup_monitor import BootUpMonitor
from ifm3dpy.device import O3R, Error

PASSWORD = "Colloportus"
TEST_PORT = 8080


def read_ssh_public_key(filename="id_o3r.pub"):
    """Read the SSH public key from the user's .ssh directory."""
    key_path = os.path.join(os.path.expanduser("~/.ssh"), filename)
    with open(key_path, "r") as f:
        return f.read().strip()


def main(ip):
    o3r = O3R(ip)
    bootup_monitor = BootUpMonitor(o3r=o3r, timeout=240, wait_time=1)
    sealed_box = o3r.sealed_box()
    print("Connected to O3R device")

    firewall_activated_by_script = False

    try:
        # Set a temporary password (remove any existing one first)
        if sealed_box.is_password_protected():
            sealed_box.remove_password(password=PASSWORD)
        sealed_box.set_password(new_password=PASSWORD, old_password=None)
        print("Password set successfully")

        # Activate the firewall if needed (requires a reboot)
        firewall_active = o3r.get(["/device/network/firewall/active"])["device"][
            "network"
        ]["firewall"]["active"]
        if firewall_active:
            print("Firewall is already active")
        else:
            print("Firewall is not active, activating it")
            sealed_box.set(
                password=PASSWORD,
                configuration={"device": {"network": {"firewall": {"active": True}}}},
            )
            o3r.reboot()
            bootup_monitor.wait_for_reboot()
            firewall_activated_by_script = True

        # Open the test port for TCP and UDP
        user_ports = [
            {"port": TEST_PORT, "protocol": "tcp"},
            {"port": TEST_PORT, "protocol": "udp"},
        ]
        sealed_box.set(
            password=PASSWORD,
            configuration={
                "device": {
                    "network": {
                        "interfaces": {"eth0": {"firewall": {"userPorts": user_ports}}}
                    }
                }
            },
        )
        print("Firewall ports configured successfully")

        # Add the local SSH public key
        ssh_key = read_ssh_public_key("id_o3r.pub")
        sealed_box.set(
            password=PASSWORD,
            configuration={"device": {"network": {"authorized_keys": ssh_key}}},
        )
        print("Authorized key added successfully")

    except Error as e:
        print("Error configuring device:", e)

    finally:
        # Deactivate the firewall again if the script activated it (requires a reboot)
        if firewall_activated_by_script:
            print("Deactivating firewall again")
            sealed_box.set(
                password=PASSWORD,
                configuration={"device": {"network": {"firewall": {"active": False}}}},
            )
            o3r.reboot()
            bootup_monitor.wait_for_reboot()

        # Remove the temporary password
        sealed_box.remove_password(password=PASSWORD)
        if sealed_box.is_password_protected():
            raise Exception("Password removal failed")
        print("Password has been removed successfully")


if __name__ == "__main__":
    DEVICE_IP = "192.168.0.69"
    main(DEVICE_IP)
