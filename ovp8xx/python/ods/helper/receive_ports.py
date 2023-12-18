#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from ifm3dpy.device import O3R
from ifm3dpy.device import Error as ifm3dpy_error
import itertools

import logging

logger = logging.getLogger(__name__)


def get_app_port(o3r: O3R, app: str) -> int:
    logger.debug(f"Return TCPPort number from {app}")

    try:
        port = o3r.get([f"/applications/instances/{app}/data/pcicTCPPort"])[
            "applications"
        ]["instances"][app]["data"]["pcicTCPPort"]
    except ifm3dpy_error:
        return None
    else:
        return int(port)


def get_head_port(o3r: O3R, port: str) -> int:
    logger.debug(f"Return TCPPort number from {port}")

    try:
        port = o3r.get([f"/ports/{port}/data/pcicTCPPort"])["ports"][port]["data"][
            "pcicTCPPort"
        ]
    except ifm3dpy_error:
        return None
    else:
        return int(port)


def get_app_ports(o3r: O3R) -> list:
    logger.debug("Getting TCP app ports")

    try:
        apps = o3r.get(["/applications/instances"])["applications"]["instances"]
    except ifm3dpy_error:
        return []
    else:
        return [apps[app]["data"]["pcicTCPPort"] for app in apps]


def get_head_tcp_ports(o3r: O3R) -> list:
    logger.debug("Getting TCP hardware ports")

    try:
        ports = o3r.get(["/ports"])["ports"]
        return [ports[port]["data"]["pcicTCPPort"] for port in ports]

    except KeyError:
        logger.error("No ports connected")
        return []


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    o3r = O3R()

    app_ports = get_app_ports(o3r)
    hardware_ports = get_head_tcp_ports(o3r)

    for tcp_port in itertools.chain(hardware_ports, app_ports):
        logger.debug(tcp_port)

    logger.debug(f"Get TCPPort from port2: { get_head_port(o3r, 'port2')}")
    logger.debug(f"Get TCPPort from app0: { get_app_port(o3r, 'app0')}")


if __name__ == "__main__":
    main()
