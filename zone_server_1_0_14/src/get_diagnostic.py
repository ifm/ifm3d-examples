#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
from ifm3dpy import O3R, FrameGrabber
import json
import time
import logging

logger = logging.getLogger(__name__)


class O3RDiagnostic:
    def __init__(self, o3r: O3R):
        self._o3r = o3r
        self._fg = None
        self.diagnostic = {}

    def update_diagnostic(self, filter: dict):
        """If the filter is set to {}, all diagnostic will be retrieved.
        Parameters:
            filter (dict): the filter mask defining which error messages will be retrieved.
                For example, setting to {"state": "active"} will retrieve all active errors.
                If the filter is set to {}, all diagnostic will be retrieved.
        """
        try:
            # logger.debug(
            # "Poll O3R diagnostic data using defined filter."
            # )
            self.diagnostic = self._o3r.get_diagnostic_filtered(filter)
        except Exception as e:
            raise (e)

    def _async_diag_callback(self, id, message):
        logger.error(f"Got error {id} with content: {message}")
        self.diagnostic = message

    def start_async_diag(self, callback=_async_diag_callback):
        """Start the diagnostic asynchronous stream.
        The _async_diag_callback function will be called for any error received.
        """
        self._fg = FrameGrabber(self._o3r, 50009)
        self._fg.on_async_error(callback)
        logger.debug(
            "Start async diagnostic monitoring. \nErrors ids and descriptions will be logged."
        )
        self._fg.start([])

    def stop_async_diag(self):
        self._fg.stop()

    def get_filtered_diagnostic_msgs(
        self,
        filter: dict = {"state": "active"},
        params_to_return: list = ["id", "name", "state", "source"],
    ):
        self.update_diagnostic(filter=filter)
        diagnostic = self.diagnostic
        filtered_diags = []
        for event in diagnostic["events"]:
            filtered_diags.append({k: event[k] for k in params_to_return})
        return filtered_diags


# %%
def main():
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")

    o3r = O3R()

    o3r_diagnostic = O3RDiagnostic(o3r)

    # Check the diagnostic once for active errors
    o3r_diagnostic.update_diagnostic({"state": "active"})
    logger.debug(o3r_diagnostic.diagnostic)

    # Start monitoring the diagnostic asynchronously
    o3r_diagnostic.start_async_diag()
    time.sleep(30)
    o3r_diagnostic.stop_async_diag()


if __name__ == "__main__":
    main()
