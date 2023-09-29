#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import cv2
import numpy as np

import ifm3dpy


class OCVWindow:

    def __init__(self, window_name: str):
        self.window_name = window_name
        self.window_created = False
        self.keypress = -1

    def open(self):
        cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        self.window_created = True

    def update_image(self, image: np.ndarray = np.zeros((100, 100, 3), np.uint8), text=[]):
        keypress = -1
        if self.window_created:
            if image is not None:
                cv2.imshow(self.window_name, image)
                keypress = cv2.waitKey(1)
        else:
            raise Exception(
                "Window not created yet. Call create_window() first")
        self.keypress = keypress
        if self.keypress != -1:
            if self.keypress in [27, ord("q")]:  # 'esc' or 'q'
                self.window_created = False
                self.destroy()

    def destroy(self):
        try:
            cv2.destroyWindow(self.window_name)
        except Exception as err:
            # recurrent issues with closing windows:
            if "578" in str(err):  # on linux
                # OpenCV(4.7.0) /io/opencv/modules/highgui/src/window_QT.cpp:578:
                # error: (-27:Null pointer) NULL guiReceiver
                # (please create a window) in function 'cvDestroyWindow'
                pass
            elif "window_w32.cpp:1261" in str(err):  # on Win10
                pass
            else:
                raise err
        self.window_created = False


class ODSViz:
    def __init__(self, o3r: ifm3dpy.O3R, instructions=""):
        self.o3r = o3r
        self.count = 0
        self.update_pause = 0
        self.instructions = instructions
        self.ports = self.o3r.get(["/ports"])["ports"]
        self.get_active_ports()

    def get_active_ports(self, config:dict = {}):
        if not config:
            app0 = self.o3r.get(["/applications/instances/app0"]
                            )["applications"]["instances"]["app0"]
        else:
            app0 = config["applications"]["instances"]["app0"]
        self.diags = self.o3r.get_diagnostic_filtered({"state": "active"})
        # enumerate active_ports
        self.active_ports = {}
        for port in app0["configuration"]["activePorts"]:
            self.active_ports[port] = {
                "xy": [self.ports[port]["processing"]["extrinsicHeadToUser"]["trans"+axis] for axis in "XY"]
            }
        # zone config
        self.zone_coordinates = app0["configuration"]["zones"]["zoneCoordinates"]

    def draw_text(
        self,
        img,
        *,
        text,
        uv_top_left,
        color=(255, 255, 255),
        fontScale=1,
        thickness=1,
        fontFace=cv2.FONT_HERSHEY_PLAIN,
        outline_color=(0, 0, 0),
        line_spacing=1.5,
    ):
        """
        Draws multiline with an outline.
        """
        assert isinstance(text, str)

        uv_top_left = np.array(uv_top_left, dtype=float)
        assert uv_top_left.shape == (2,)

        for line in text.splitlines():
            (w, h), _ = cv2.getTextSize(
                text=line,
                fontFace=fontFace,
                fontScale=fontScale,
                thickness=thickness,
            )
            uv_bottom_left_i = uv_top_left + [0, h]
            org = tuple(uv_bottom_left_i.astype(int))

            if outline_color is not None:
                cv2.putText(
                    img,
                    text=line,
                    org=org,
                    fontFace=fontFace,
                    fontScale=fontScale,
                    color=outline_color,
                    thickness=thickness * 3,
                    lineType=cv2.LINE_AA,
                )
            cv2.putText(
                img,
                text=line,
                org=org,
                fontFace=fontFace,
                fontScale=fontScale,
                color=color,
                thickness=thickness,
                lineType=cv2.LINE_AA,
            )

            uv_top_left += [0, h * line_spacing]

    def render_visual(self, raw_occupancy_grid: np.ndarray, zones_occupied, upscale_factor=5):

        self.count += 1
        if self.update_pause and (self.count % self.update_pause == 0):
            self.get_active_ports()

        # Increase contrast in visualization:
        occupancy_grid = raw_occupancy_grid - 51
        # Allow visualization to be colorful
        occupancy_grid = cv2.cvtColor(occupancy_grid, cv2.COLOR_GRAY2BGR)
        # Make visualization higher resolution. Use no interpolation.
        occupancy_grid = cv2.resize(
            occupancy_grid, np.array(occupancy_grid.shape[:2]) * upscale_factor, interpolation=0)
        # Add gridlines 1m apart
        for offset in range(-5, 5):
            occupancy_grid[(100 + offset * 20) * upscale_factor, :] += 50
            occupancy_grid[:, (100 + offset * 20) * upscale_factor] += 50

        # Paint zones on visualization
        colors = (
            ((0, 0, 150), (0, 0, 255)),
            ((0, 150, 150), (0, 255, 255)),
            ((0, 150, 0), (0, 255, 0)),
        )
        for zone, zone_occupied, color in list(
            zip(
                self.zone_coordinates,
                zones_occupied,
                colors,
            )
        )[::-1]:
            contour = [
                np.array((np.array(zone) * 20 + 100) *
                         upscale_factor, dtype=np.int32)
            ]
            mask = np.zeros_like(occupancy_grid)
            cv2.drawContours(mask, contour, -1,
                             np.array(color[zone_occupied])/5, -1)
            occupancy_grid = np.uint8(np.minimum(
                np.uint16(occupancy_grid) + mask, np.ones_like(occupancy_grid)*255))
            occupancy_grid = cv2.drawContours(
                occupancy_grid, contour, 0, color[zone_occupied], 1
            )
        # Rotate and flip occupancy grid to feel right for desktop testing
        occupancy_grid = cv2.rotate(
            (occupancy_grid), cv2.ROTATE_90_COUNTERCLOCKWISE)
        occupancy_grid = cv2.flip((occupancy_grid), 1)

        text_lines = [
            "Zones: " + str(zones_occupied),
            "Active Diagnostic Items: "]
        if self.diags["events"]:
            text_lines += [
                f"  {event['name']} from {event['source'].split('/')[-1]}" for event in self.diags["events"]]
        else:
            text_lines += ["  None"]
        text = "\n".join(text_lines)+"\n\n"+self.instructions
        self.draw_text(
            img=occupancy_grid,
            text=text,
            uv_top_left=(10, 10))

        for port, info in self.active_ports.items():
            port_n = int(port[-1])
            camera_position = info["xy"]
            camera_position_px = (
                (-1*np.array(camera_position)*20+100)*upscale_factor)[::-1]

            self.draw_text(
                img=occupancy_grid,
                text=str(port_n),
                fontScale=1,
                thickness=1,
                color=(100, 100, 200),
                uv_top_left=camera_position_px-np.array((5, 5))
            )

        return occupancy_grid
