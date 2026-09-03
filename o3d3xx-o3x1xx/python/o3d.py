# -*- coding: utf-8 -*-
#############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
import time

import cv2
from ifm3dpy.device import O3D
from ifm3dpy.framegrabber import FrameGrabber, buffer_id
from render_buffers import label_and_stitch_images, render

if __name__ != "__main__":
    print(
        """
############ O3X example code ###############
      Script was accidentally imported.
  Simply run the code directly as a script,
        or interactively. Exiting...
#############################################
"""
    )
    exit(0)

# %%
ip = "192.168.0.69"
o3d = O3D(ip)

# %%
trigger_mode = 2  # 1: Continuous, 2: Software Trigger
framerate = 20  # fps

o3d.from_json(
    {
        "ifm3d": {
            "Apps": [
                {
                    "Imager": {
                        "FrameRate": str(framerate),
                    },
                    "TriggerMode": str(trigger_mode),
                }
            ]
        }
    }
)
trigger_mode = o3d.to_json()["ifm3d"]["Apps"][0]["TriggerMode"]

# %%

visualization_window_name = "O3D-viz 'ESC' to exit 'x' to save a frame"
buffers = [
    buffer_id.RADIAL_DISTANCE_IMAGE,
    buffer_id.NORM_AMPLITUDE_IMAGE,
    buffer_id.AMPLITUDE_IMAGE,
    buffer_id.CONFIDENCE_IMAGE,
    buffer_id.CARTESIAN_X_COMPONENT,
    buffer_id.CARTESIAN_Y_COMPONENT,
    buffer_id.CARTESIAN_Z_COMPONENT,
]

exiting = False
first_frame_received = False


def on_new_frame(frame):
    global first_frame_received
    global exiting

    images = {buffer: render(frame, buffer) for buffer in buffers}
    combined_image = label_and_stitch_images(images)

    if not first_frame_received:
        # make the window resizable
        cv2.namedWindow(visualization_window_name, cv2.WINDOW_NORMAL)
        first_frame_received = False
    cv2.imshow(visualization_window_name, combined_image)

    key = cv2.waitKey(1)
    # press ESC to exit
    if key == 27:
        exiting = True
        fg.stop()
        cv2.destroyAllWindows()
    # press x to save scene
    elif key == ord("x"):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"o3x_all_buffers_{timestamp}.png"
        cv2.imwrite(filename, combined_image)
        print(f"Saved frame to {filename}")


fg = FrameGrabber(o3d)
fg.start(buffers)
fg.on_new_frame(on_new_frame)

try:
    while not exiting:
        # iterate over frames
        if trigger_mode == 2:
            fg.sw_trigger()
        time.sleep(1.0 / framerate)
except KeyboardInterrupt:
    pass
except Exception as e:
    print("Error during frame acquisition: " + str(e))
    raise e
fg.stop()
cv2.destroyAllWindows()
