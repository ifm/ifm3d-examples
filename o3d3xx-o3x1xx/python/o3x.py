# -*- coding: utf-8 -*-
# #############################################
# Copyright 2025-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%

import time
from pprint import pprint

import cv2
from ifm3dpy.device import O3X
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

ip = "192.168.0.69"
o3x = O3X(ip)

# %%
# This cell will fail if the device is not reachable
config = o3x.to_json()
pprint(config)
print(f"Available imager types for O3X at {ip}:")
print(o3x.imager_types())

# %%
# Reboot the device if needed
if input(f"restart the O3X unit at {ip}?, Enter 'y': ") == "y":
    o3x.reboot()
    time.sleep(30)

# %%
trigger_mode = 1  # 1: Continuous, 2: Software Trigger
framerate = 20  # fps

# max viable trigger rate is sometimes lower than max continuous framerate
if trigger_mode == 2:
    framerate = min(framerate, 10)

config_activate_all_buffers = {
    "ifm3d": {
        "Apps": [
            {
                # # These are some defaults
                "Imager": {
                    "Type": "upTo07m_low",
                    "ExposureTime": "1000",
                    "FrameRate": str(framerate),
                },
                # #set all buffers to be available:
                "TriggerMode": str(trigger_mode),
                "OutputAmplitudeImage": "true",
                "OutputConfidenceImage": "true",
                "OutputDistanceImage": "true",
                "OutputDistanceNoiseImage": "true",
                "OutputGrayscaleImage": "true",
                "OutputXYZImage": "true",
            }
        ]
    }
}
o3x.from_json(config_activate_all_buffers)

# %%
visualization_window_name = "O3X-viz 'ESC' to exit 'x' to save a frame"
buffers = [
    buffer_id.RADIAL_DISTANCE_IMAGE,
    buffer_id.NORM_AMPLITUDE_IMAGE,
    buffer_id.RADIAL_DISTANCE_NOISE,
    buffer_id.CARTESIAN_X_COMPONENT,
    buffer_id.CARTESIAN_Y_COMPONENT,
    buffer_id.CARTESIAN_Z_COMPONENT,
    buffer_id.CONFIDENCE_IMAGE,
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


fg = FrameGrabber(o3x)
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
