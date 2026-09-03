# -*- coding: utf-8 -*-
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from typing import List

import cv2
import numpy as np


def render(frame, id):
    try:
        buffer = frame.get_buffer(id)
    except Exception as e:
        print("Error deserializing buffer " + str(id) + ": " + str(e))
        return None
    img = cv2.applyColorMap(
        np.uint8(np.abs(buffer) * (255 / max(1, np.max(buffer)))), cv2.COLORMAP_JET
    )
    return img


def label_and_stitch_images(images: List[np.ndarray]) -> np.ndarray:
    # Determine grid size
    n = len(images)
    n_cols = int(np.ceil(np.sqrt(n)))
    n_rows = int(np.ceil(n / n_cols))
    # add title to the images in a thumbnail at the top of each image
    thumbnail_height = 30
    image_width = images[list(images.keys())[0]].shape[1]
    thumbnail_width = image_width
    labeled_images = []
    for buffer, img in images.items():
        if img is not None:
            thumbnail = np.zeros((thumbnail_height, thumbnail_width, 3), dtype=np.uint8)
            thumbnail_text = (
                str(buffer)
                .lower()
                .split(".")[1]
                .replace("_", " ")
                .replace("image", "")
                .replace("component", "")
            )
            cv2.putText(
                thumbnail,
                thumbnail_text,
                (5, 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (255, 255, 255),
                1,
            )
            labeled_img = cv2.vconcat([thumbnail, img])
            # Add 2px black border around the image
            labeled_img = cv2.copyMakeBorder(
                labeled_img, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0)
            )
            labeled_images.append(labeled_img)
    # fill the rest of the grid with black images if necessary
    while len(labeled_images) < n_cols * n_rows:
        blank_img = np.zeros(
            (
                thumbnail_height + images[list(images.keys())[0]].shape[0],
                image_width,
                3,
            ),
            dtype=np.uint8,
        )
        blank_img = cv2.copyMakeBorder(
            blank_img, 2, 2, 2, 2, cv2.BORDER_CONSTANT, value=(0, 0, 0)
        )
        labeled_images.append(blank_img)
    # create the grid
    rows = []
    for r in range(n_rows):
        row = cv2.hconcat(labeled_images[r * n_cols : (r + 1) * n_cols])
        rows.append(row)
    combined_image = cv2.vconcat(rows)
    return combined_image
