#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# This file can be run interactively, section by section
# Sections are delimited by '#%%'
# Several editors including Spyder and vscode+python are equiped to run these cells
# by simply pressing shift-enter

# %%
from ifm3dpy.framegrabber import buffer_id, FrameGrabber
import numpy as np
import cv2

import time
from functools import partial

DEFAULT_BUFFERS_OF_INTEREST = {
    "3D": {
        "dist": buffer_id.RADIAL_DISTANCE_IMAGE,
        "NAI": buffer_id.NORM_AMPLITUDE_IMAGE,
    },
    "2D": {
        "rgb": buffer_id.JPEG_IMAGE,
    },
}

# Default settings for openCV
FONT = cv2.FONT_HERSHEY_SIMPLEX
ORG = (10, 10)
FONTSCALE = 0.7
COLOR = (255, 255, 0)
THICKNESS = 2


class FrameCollector:
    def __init__(
        self,
        o3r,
        ports: list = [],
        buffers_of_interest=DEFAULT_BUFFERS_OF_INTEREST,
    ):

        self.o3r = o3r

        self.port_config = o3r.get()
        if len(ports) == 2:
            self.ports = ports
        else:
            raise ValueError("Two ports must be provided.")

        self.ports_info = {port_n: o3r.port(port_n) for port_n in self.ports}
        self.buffer_ids_of_interest = {}
        for port_n in self.ports:
            self.buffer_ids_of_interest[port_n] = buffers_of_interest[
                self.ports_info[port_n].type
            ]

        self.frame_grabbers = {}
        for port_n in self.ports:
            self.frame_grabbers[port_n] = FrameGrabber(
                o3r, self.ports_info[port_n].pcic_port
            )

        self.saved_buffer_sets = []
        self.buffer_data_set = {port_n: {} for port_n in self.ports}

        self.data_to_display = {}
        self.key_presses = []

    def _setup_opencv(self):
        # start opencv windows
        for port_n in self.ports:
            for buffer_name in self.buffer_ids_of_interest[port_n].keys():
                cv2.namedWindow(f"{buffer_name} - {port_n}", cv2.WINDOW_NORMAL)

    def show(self):
        self._setup_opencv()
        time.sleep(0.1)
        while True:
            self.key_presses = []
            if self.data_to_display:
                data_copy = self.data_to_display.copy()
                for winname, data in data_copy.items():
                    text_overlay = "Press 's' to record for analysis"
                    if len(data.shape) < 3:
                        buffer_data_color = cv2.cvtColor(
                            data.copy(), cv2.COLOR_GRAY2BGR
                        )
                    else:
                        buffer_data_color = data.copy()
                    buffer_data_with_text = cv2.putText(
                        buffer_data_color,
                        text_overlay,
                        np.array(
                            (np.array((0, 0.1)) * data.shape[0]), np.uint16
                        ).tolist(),
                        fontFace=FONT,
                        fontScale=FONTSCALE * data.shape[0] / 300,
                        color=COLOR,
                        thickness=int(THICKNESS * data.shape[0] / 300),
                    )
                    cv2.imshow(winname, np.array(buffer_data_with_text, dtype=np.uint8))
                    self.key_presses.append(cv2.waitKey(1))
                    self.data_to_display.pop(winname)
                    data_copy = {}
            else:
                pass
            # check for save
            if ord("s") in self.key_presses:
                self.saved_buffer_sets.append(self.buffer_data_set.copy())
                for port_n, saved_buffers in self.buffer_data_set.items():
                    for buffer_name, buffer_data in saved_buffers.items():
                        winname = f"{buffer_name} - {port_n} - Saved"
                        cv2.namedWindow(winname, cv2.WINDOW_NORMAL)

                        text_overlay = "Press 'Esc' to use this frame."
                        if len(buffer_data.shape) < 3:
                            buffer_data_color = cv2.cvtColor(
                                buffer_data.copy(), cv2.COLOR_GRAY2BGR
                            )
                        else:
                            buffer_data_color = buffer_data.copy()
                        buffer_data_with_text = cv2.putText(
                            buffer_data_color,
                            text_overlay,
                            ORG,
                            fontFace=FONT,
                            fontScale=FONTSCALE * buffer_data.shape[0] / 300,
                            color=COLOR,
                            thickness=int(THICKNESS * buffer_data.shape[0] / 300),
                        )
                        cv2.imshow(winname, buffer_data_with_text)

            # check for exit
            if 27 in self.key_presses:
                print("Exiting...")
                # reset the port_config and cleanup
                self.o3r.set(self.port_config)
                cv2.destroyAllWindows()
                print("Destroyed all windows")
                for port_n in self.ports:
                    self.frame_grabbers[port_n].stop()
                break
        return

    def _callback(self, port_n, frame):
        for buffer_name, buffer_id in self.buffer_ids_of_interest[port_n].items():
            buffer_data = frame.get_buffer(buffer_id)
            # some additional boilerplate for unpacking 2D data
            if self.ports_info[port_n].type == "2D" and buffer_name == "rgb":
                buffer_data = cv2.imdecode(buffer_data, cv2.IMREAD_UNCHANGED)
            self.buffer_data_set[port_n][buffer_name] = buffer_data
            winname = f"{buffer_name} - {port_n}"
            self.data_to_display[winname] = buffer_data

    def loop(self, timeout=2000):
        # set cameras to run
        o3r_port_json = {}
        for port_n in self.ports:
            o3r_port_json.update({f"{self.ports_info[port_n].port}": {"state": "RUN"}})
        self.o3r.set({"ports": o3r_port_json})
        time.sleep(0.1)

        # Start streaming frames
        for port_n in self.ports:
            self.frame_grabbers[port_n].on_new_frame(partial(self._callback, port_n))
            self.frame_grabbers[port_n].start(
                list(self.buffer_ids_of_interest[port_n].values())
            )
        self.show()


# %%
if __name__ == "__main__":
    IP_ADDR = "192.168.0.69"
    from ifm3dpy.device import O3R

    o3r = O3R(IP_ADDR)

    import atexit

    def at_exit(frame_collector):
        for port, fg in frame_collector.frame_grabbers.items():
            fg.stop()

    frame_collector = FrameCollector(o3r, ports=["port1", "port3"])
    atexit.register(partial(at_exit, frame_collector))
    frame_collector.loop()
    frame_collector.show()

# %%
