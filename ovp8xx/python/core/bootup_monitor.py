# -*- coding: utf-8 -*-
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import logging
import socket
import time

from ifm3dpy.device import O3R
from ifm3dpy.device import Error as ifm3dpy_error


class BootUpMonitor:
    """This class helps to properly monitor that the VPU is fully booted up."""

    def __init__(
        self,
        o3r: O3R,
        timeout: int = 60,
        wait_time: int = 0.5,
    ) -> None:
        self.o3r = o3r
        self._stages = ["device", "ports", "applications"]
        self._diagnostics_PCICPort = 50009
        self.timeout = timeout
        self.wait_time = wait_time
        self._ip = o3r.ip

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO, format="%(message)s")

    def wait_for_diagnostics(self, retry_delay=0.5):
        """Waits until the diagnostics service is available at the given IP and port."""
        while True:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Optional: set timeout to avoid indefinite hanging
                sock.settimeout(1)
                result = sock.connect_ex((self._ip, self._diagnostics_PCICPort))
                if result == 0:
                    self.logger.info("Diagnostics service available.")
                    return
            time.sleep(retry_delay)

    def retrieve_boot_diagnostic(self):
        self.logger.info("Retrieving diagnostics: \n")
        for error in self.o3r.get_diagnostic_filtered({"state": "active"})["events"]:
            self.logger.warning("Active errors: %s, %s", error["id"], error["name"])

    def monitor_VPU_bootup(self) -> bool:
        """
        Check that the VPU completes it's boot sequence before
        attempting to initialize an application.
        Sequence goes:
        /device/diagnostic/confInitStages: 'device' --> 'ports' --> 'applications'
        Diagnostic query for active errors

        Args:
            o3r (ifm3dpy.O3R): O3R handle
            timeout (int, optional): Maximum time expected for bootup sequence in seconds. Defaults to 60.
            wait_time (int, optional): how long to pause between queries to the VPU. Defaults to .5.

        Raises:
            TimeoutError: If no valid response is received from VPU within the timeout duration.
        Returns:
            True if the VPU is fully booted
        """
        if len(self._stages) == 0:
            raise RuntimeError("please use a non empty list of stages")

        self.logger.debug("Monitoring bootup sequence: ready to connect.")

        start = time.perf_counter()
        config = None
        while time.perf_counter() - start < self.timeout:
            try:
                config = self.o3r.get()
                self.logger.debug("Connected.")
            except ifm3dpy_error:
                self.logger.debug("Awaiting data from VPU...")

            if config:
                confInitStages = config["device"]["diagnostic"]["confInitStages"]
                if all(x in self._stages for x in confInitStages):
                    self.wait_for_diagnostics(retry_delay=0.5)
                    self.logger.info("VPU fully booted.")
                    self.retrieve_boot_diagnostic()
                    return True
                if "ports" in confInitStages:
                    self.logger.debug("Ports recognized")
                elif "device" in confInitStages:
                    self.logger.debug("Device recognized")
            time.sleep(self.wait_time)
        raise TimeoutError("Process timed out waiting for VPU to boot")

    def __enter__(self):
        self.logger.info("Waiting for VPU to boot")
        return self

    def __exit__(self, type, value, traceback):
        self.logger.info(
            "Bootup monitoring finished. Check the logs to verify bootup status."
        )

    # %%


def main():
    IP = "192.168.0.69"
    o3r = O3R(IP)
    bootup_monitor = BootUpMonitor(o3r)
    bootup_monitor.monitor_VPU_bootup()


if __name__ == "__main__":
    main()
