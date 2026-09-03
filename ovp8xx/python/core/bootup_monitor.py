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

    _READY_STATUS = "OPERATE"

    def __init__(
        self,
        o3r: O3R,
        timeout: int = 60,
        wait_time: int = 0.5,
    ) -> None:
        self.o3r = o3r
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

    def _get_device_status(self):
        """Return the current device status when available."""
        status = self.o3r.get(["/device/status"])
        if isinstance(status, dict):
            return status.get("device", {}).get("status")
        return status

    def wait_until_offline(self, timeout: int = 60) -> bool:
        """
        Wait until the VPU is no longer in the ready state (i.e. a reboot has
        actually started). This is required after issuing `o3r.reboot()` because
        the command returns immediately, while the VPU still reports its previous
        `OPERATE` status for a short time.

        Returns:
            True once the VPU has left the ready state, False on timeout.
        """
        start = time.perf_counter()
        while time.perf_counter() - start < timeout:
            try:
                status = self._get_device_status()
            except ifm3dpy_error:
                status = None
            if status != self._READY_STATUS:
                self.logger.info("VPU is offline/rebooting.")
                return True
            time.sleep(self.wait_time)
        self.logger.warning("VPU never left the ready state within timeout.")
        return False

    def wait_for_reboot(self, offline_timeout: int = 60) -> bool:
        """
        Monitor a full reboot cycle: first wait for the VPU to go offline, then
        wait for it to boot back up to the ready state.

        Returns:
            True if the VPU rebooted and is fully booted again.
        """
        if not self.wait_until_offline(timeout=offline_timeout):
            return False
        return self.monitor_VPU_bootup()

    def monitor_VPU_bootup(self) -> bool:
        """
        Check that the VPU completes it's boot sequence before
        attempting to initialize an application.
        Readiness is determined from `/device/status` reaching `OPERATE`.
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
        self.logger.debug("Monitoring bootup sequence: ready to connect.")

        start = time.perf_counter()
        last_status = None
        while time.perf_counter() - start < self.timeout:
            try:
                status = self._get_device_status()
                self.logger.debug("Connected.")
            except ifm3dpy_error:
                status = None
                self.logger.debug("Awaiting data from VPU...")

            if status:
                if status != last_status:
                    self.logger.info("Current device status: %s", status)
                    last_status = status

                if status == self._READY_STATUS:
                    self.wait_for_diagnostics(retry_delay=0.5)
                    self.logger.info("VPU fully booted.")
                    self.retrieve_boot_diagnostic()
                    return True
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
