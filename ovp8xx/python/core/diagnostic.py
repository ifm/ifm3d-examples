# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This script demonstrates the possibilities for working with diagnostics
# in an O3R system. It showcases how to retrieve diagnostics using the
# `get_diagnostic_filtered` method and how to handle diagnostics asynchronously
# using a callback function. The script also includes functionality to filter
# and display diagnostics based on severity levels.
#############################################
import json
import time

from ifm3dpy.device import O3R, Error
from ifm3dpy.framegrabber import FrameGrabber


class DiagnosticHandler:
    def __init__(self, ip: str):
        self.o3r = O3R(ip)
        self.diag_fg = FrameGrabber(self.o3r, 50009)

    def start_diagnostics(self):
        """Start diagnostic monitoring."""
        self.diag_fg.on_async_error(callback=self.async_diagnostic_callback)
        print(
            "Starting async diagnostic monitoring. \nErrors ids and descriptions will be logged."
        )
        self.diag_fg.start([])

    def stop_diagnostics(self):
        """Stop diagnostic monitoring."""
        self.diag_fg.stop()

    def get_diagnostic_filtered(self, filter_mask: json = {}) -> dict:
        """Retrieve diagnostics filtered by the specified filter mask.

        :param filter_mask (json): The filter mask defining which error messages will be retrieved.
            For example, setting to {"state": "active"} will retrieve all active errors.
            If the filter is set to {}, all diagnostics will be retrieved.
        :return: The diagnostics filtered with the filter_mask.
        """
        try:
            print(f"Poll O3R diagnostic data with filter {filter_mask}.")
            return self.o3r.get_diagnostic_filtered(filter_mask)
        except Error as err:
            print("Error when getting diagnostic data.")
            raise err

    @staticmethod
    def async_diagnostic_callback(
        id: int, message: str, severity: str = "minor"
    ) -> None:
        """
        Callback to print diagnostic messages filtered by severity.

        Args:
            id (int): Diagnostic ID.
            message (str): Diagnostic message in JSON format.
            severity (str): Severity level to filter messages.
                            Options: ["critical", "major", "minor", "info"].
        """
        severity_levels = ["critical", "major", "minor", "info"]
        if severity not in severity_levels:
            print(f"Invalid severity level: {severity}. Defaulting to 'major'.")
            severity = "major"

        # Determine the severity levels to display
        severity_index = severity_levels.index(severity)
        allowed_severities = severity_levels[: severity_index + 1]

        diagnostic = json.loads(message)
        # print(json.dumps(diagnostic, indent=4))  # Debug: Print full diagnostic message

        # Extract groups and check for relevant issues
        groups = diagnostic.get("groups", {})
        relevant_groups = {
            group: status
            for group, status in groups.items()
            if status in allowed_severities
        }

        # Extract events and filter by severity
        events = diagnostic.get("events", [])
        relevant_events = [
            event for event in events if event["severity"] in allowed_severities
        ]

        if not relevant_groups and not relevant_events:
            return  # No relevant diagnostics, so exit early

        # Print groups with relevant severities
        if relevant_groups:
            print(
                f"\n🚨 Diagnostic Alert 🚨 (Severity: {severity}) happened with timestamp: {diagnostic['timestamp']} \n"
            )
            print("Affected Groups:")
            for group, status in relevant_groups.items():
                print(f" - {group}: {status}")
            # Print diagnostic events with relevant severities
            if relevant_events:
                print("\nDiagnostic Events:")
                for event in relevant_events:
                    # For the sake of space, we are only printing out
                    # the most important information. We are ignoring
                    # the statistics and the targets.
                    filtered_diag = {
                        "id": event["id"],
                        "name": event["name"],
                        "severity": event["severity"],
                        "description": event["description"],
                        "source": event["source"],
                        "state": event["state"],
                        "timestamp": diagnostic["timestamp"],
                    }
                    if filtered_diag["severity"] == "critical":
                        print(
                            "⚠️ Critical diagnostic appeared! Stop the robot and follow the handling strategy.\n"
                        )  # here you can add your own handling strategy and stopping the robot
                    print(json.dumps(filtered_diag, indent=4))


def main(ip: str) -> None:
    o3r_diagnostic = DiagnosticHandler(ip)

    get_current_diagnostic = o3r_diagnostic.get_diagnostic_filtered({"state": "active"})
    print(
        f"Current active diagnostics:\n{json.dumps(get_current_diagnostic, indent=4, sort_keys=True)}"
    )
    time.sleep(2)

    # Loop for 5 seconds, displaying only the relevant groups
    start_time = time.time()
    while time.time() - start_time < 5:
        get_current_diagnostic = o3r_diagnostic.get_diagnostic_filtered(
            {"state": "active"}
        )
        groups = get_current_diagnostic.get("groups", {})

        # Display the groups status for existing ports and applications
        filtered_groups = {
            key: value for key, value in groups.items() if value != "not_available"
        }
        print(
            f"Current active diagnostic groups (filtered):\n{json.dumps(filtered_groups, indent=4, sort_keys=True)}"
        )
        time.sleep(1)  # Wait 1 second before the next iteration

    # Callback to monitor Diagnostics
    o3r_diagnostic.start_diagnostics()
    try:
        print("Press Ctrl+C to stop diagnostic monitoring.")
        while True:
            pass  # Keep the script running to monitor diagnostics

    except KeyboardInterrupt:
        print("Stopping diagnostic monitoring.")
        o3r_diagnostic.stop_diagnostics()


if __name__ == "__main__":
    IP = "192.168.0.69"
    main(ip=IP)
