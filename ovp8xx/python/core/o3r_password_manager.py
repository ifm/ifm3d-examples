# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import os

from ifm3dpy.device import O3R, Error


def read_ssh_public_key(filename="id_o3r.pub"):
    """Read the SSH public key from the user's .ssh directory."""
    ssh_path = os.path.expanduser("~/.ssh")
    key_path = os.path.join(ssh_path, filename)
    with open(key_path, "r") as f:
        return f.read().strip()


def check_vpu_protected_status(sealed_box):
    """Check if the VPU is password protected."""
    try:
        is_protected = sealed_box.is_password_protected()
        print(f"VPU {'is' if is_protected else 'is not'} password protected")
        return is_protected
    except RuntimeError as e:
        print("Error checking VPU password protection status:", e)
        return False


def main(ip):
    o3r = O3R(ip)

    sealed_box = o3r.sealed_box()
    print("Connected to O3R device")

    # Get and display the public key
    sealed_box.get_public_key()
    # print("Public key:", public_key)

    # Set a temporary password
    try:
        sealed_box.set_password(new_password="Colloportus", old_password=None)
        print("Password set successfully")
    except Error as e:
        print("Error setting password:", e)
        return

    # Check password protection status
    check_vpu_protected_status(sealed_box)
    test_port = 8080

    # Set only the firewall configuration
    user_ports = [
        {"port": test_port, "protocol": "tcp"},
        {"port": test_port, "protocol": "udp"},
    ]
    firewall_config = {
        "device": {
            "network": {"interfaces": {"eth0": {"firewall": {"userPorts": user_ports}}}}
        }
    }

    try:
        sealed_box.set(password="Colloportus", configuration=firewall_config)
        print("Firewall configuration set successfully")
    except Error as e:
        print("Error setting firewall configuration:", e)

    # add authorized_keys
    ssh_key = read_ssh_public_key("id_o3r.pub")
    auth_key_config = {"device": {"network": {"authorized_keys": ssh_key}}}
    sealed_box.set(password="Colloportus", configuration=auth_key_config)

    # Remove the password again if needed
    try:
        sealed_box.remove_password(password="Colloportus")
        print("Password removed successfully")
    except Error as e:
        print("Error removing password:", e)

    # Final check
    check_vpu_protected_status(sealed_box)


if __name__ == "__main__":
    DEVICE_IP = "192.168.0.69"
    main(DEVICE_IP)
