#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import json
import logging
from datetime import datetime

from ifm3dpy.device import O3R
from ifm3dpy.device import Error as ifm3dpy_error
from ifm3dpy.framegrabber import FrameGrabber


class O3RDiagnostic:
    """Helper functions for retrieving diagnostics when requested
    or asynchronously."""

    def __init__(self, o3r: O3R, log_to_file: bool):
        self._o3r = o3r
        self._fg = None
        self.diagnostic = []
        ###########################
        # Logger configuration:
        self.logger = logging.getLogger(__name__)
        _log_format = "%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s"
        _log_datefmt = "%y-%m-%d %H:%M:%S"
        if log_to_file:
            logging.basicConfig(
                filename=f'{datetime.now.strftime("%Y%m%d")}_{datetime.now.strftime("%H%M%S")}_diagnostic.log',
                format=_log_format,
                datefmt=_log_datefmt,
            )
        else:
            logging.basicConfig(format=_log_format, datefmt=_log_datefmt)
        self.logger.setLevel(logging.INFO)
        ###########################

    def get_diagnostic_filtered(self, filter_mask: json = {}) -> dict:
        """If the filter is set to {}, all diagnostic will be retrieved.

        :param filter_mask (json): the filter mask defining which error messages will be retrieved.
            For example, setting to {"state": "active"} will retrieve all active errors.
            If the filter is set to {}, all diagnostic will be retrieved.
        :return: the diagnostic, filtered with the filter_mask
        """
        try:
            self.logger.info(
                f"Poll O3R diagnostic data with filter {filter_mask}.")
            return self._o3r.get_diagnostic_filtered(filter_mask)
        except ifm3dpy_error as err:
            self.logger.exception("Error when getting diagnostic data.")
            raise err

    def _async_diag_callback(self, id: int, message: str):
        """Callback to log active errors.

        :param id (int): ID of Error Message
        :param message (str): Whole Diagnostic Information
        """
        self.logger.error("Recieved diagnostic message via callback with id=%s, content=%s", id, message)
        self.diagnostic = {"id": id, "message": message}
        # Here the user should add custom error handling.

    def start_async_diag(self):
        """Start the diagnostic asynchronous stream.
        The _async_diag_callback function will be called for any error received.
        """
        self._fg = FrameGrabber(self._o3r, 50009)
        self._fg.on_async_error(callback=self._async_diag_callback)
        self.logger.info(
            "Starting async diagnostic monitoring. \nErrors ids and descriptions will be logged."
        )
        self._fg.start([])

    def stop_async_diag(self):
        """Stops the Framegrabber listening to the diagnostic information"""
        self.logger.info("Stopping async diagnostic monitoring.")
        self._fg.stop()


def main():
    #############################
    # Configure the objects.
    # Make sure to edit for your
    # IP address.
    #############################
    IP = "192.168.0.69"
    o3r = O3R(IP)
    o3r_diagnostic = O3RDiagnostic(o3r, log_to_file=False)

    #############################
    # Requesting diagnostic data
    #############################
    o3r_diagnostic.logger.info(
        f"Currently active errors: {o3r_diagnostic.get_diagnostic_filtered({'state': 'active'})}"
    )

    #############################
    # Starting the asynchronous
    # diagnostic monitoring. Any
    # new error will be logged.
    # Note that this function should
    # be customized to handle specific
    # error handling in the user
    # applaition
    #############################

    o3r_diagnostic.start_async_diag()
    while True:
        try:
            pass
        except KeyboardInterrupt:
            o3r_diagnostic.stop_async_diag()
            o3r_diagnostic.logger.info(
                "You reached the end of the O3R diagnostic tutorial! "
            )
            break


if __name__ == "__main__":
    main()
