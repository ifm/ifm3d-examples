#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %% Import Libraries

import math
import logging
from pathlib import Path, PosixPath

import h5py
import numpy as np
from matplotlib import pyplot as plt
from scipy.spatial import ConvexHull
import skimage.measure
import skimage.color
import skimage.filters


logger = logging.getLogger(__name__)
# %%


def get_data_from_h5(filepath: PosixPath) -> tuple:

    with h5py.File(filepath, "r") as data:
        streams = list(data["streams"])
        logger.info(f'available streams: {list(data["streams"])}')

        stream_2d_left = data["streams"]["o3r_rgb_0"]
        stream_2d_right = data["streams"]["o3r_rgb_1"]
        stream_3d_left = data["streams"]["o3r_tof_0"]
        stream_3d_right = data["streams"]["o3r_tof_1"]
        stream_ods = data["streams"]["o3r_app_ods_0"]

        data_2d_left = np.asarray(stream_2d_left)
        data_2d_right = np.asarray(stream_2d_right)
        data_3d_left = np.asarray(stream_3d_left)
        data_3d_right = np.asarray(stream_3d_right)
        data_ods = np.asarray(stream_ods)

        for s in streams:
            logger.info(f"stream: {s}")
            logger.info(f"stream content: {data['streams'][s].dtype} \n")

        return data_2d_left, data_2d_right, data_3d_left, data_3d_right, data_ods


def get_distance_map_data(data_ods: np.ndarray, roi: list = [85, 115]) -> tuple:
    """
    Retrieves the distance map of a recorded iVA dataset

    Args:
        stream_ods (np.ndarray): input data stream ODS

    Returns:
        tuple: 'time vs distance' of a recorded data
    """

    data_ods = np.array(data_ods[:]["image"])
    total_occupancy_grids = data_ods.shape[0]
    rows_in_occupancy_grid = data_ods.shape[1]

    #  We are interested in the frames where the object is detected inside in ROI
    frames = []
    distance_map = np.zeros(data_ods[:, 0, :].shape)

    for occupancy_grid in range(total_occupancy_grids):
        for row in range(rows_in_occupancy_grid):

            idx = np.nonzero(data_ods[occupancy_grid, row, :] > 127)[
                0
            ]  # non-zero values per row

            if idx.size == 0:  # Non non-zero value found in a row of occupancy grid
                distance_map[occupancy_grid, row] = 200
            else:
                distance_map[occupancy_grid, row] = idx[0]
                if (
                    roi[0] <= row <= roi[1]
                ):  # ROI is considered as 85 to 115 rows in occupancy grid
                    frames.append(occupancy_grid)

    distance_map = -distance_map  # invert map
    frames = sorted(list(set(frames)))
    return distance_map, frames


def connected_components(gray_image: np.ndarray) -> tuple:
    """evaluate the connected components on a gray scale image

    Args:
        gray_image (np.ndarray): input image

    Returns:
        tuple: label images and counter
    """
    binary_mask = gray_image > 127
    labeled_image, count = skimage.measure.label(binary_mask, return_num=True)
    return labeled_image, count


def get_obj_pos(obj):
    coords = obj["coords"]
    x_coord, y_coord = None, None

    try:
        hull = ConvexHull(coords)
        for v in hull.vertices:
            if x_coord == None and y_coord == None:
                x_coord = coords[v][0]
                y_coord = coords[v][1]
            else:
                if (
                    coords[v][1] < y_coord
                ):  # check difference in y coordinates only not Euclidean distance
                    x_coord = coords[v][0]
                    y_coord = coords[v][1]
    except Exception as e:
        logger.warning(e)
        pass
    return x_coord, y_coord


def distance_tracker(data_ods: np.ndarray, frames: list, roi: list = [85, 115]):
    """Distance from user coordinate frame origin to the first object detected in ROI vs Time

    Args:
        data_ods (np.ndarray): input data stream ODS
        frames (list): frames where object is detected in ROI

    Returns:
        tuple: list of frames, coordinates of nearest object of interest
    """

    check_bbox = True
    check_centroid = False
    frame_detected = []
    coordinates = []

    for f in frames:
        occ_frame = data_ods[f]["image"]
        labeled_image, _ = connected_components(occ_frame)
        object_features = skimage.measure.regionprops(labeled_image)

        for obj in object_features:
            if check_bbox:
                # (min_row, min_col, max_row, max_col)
                # https://scikit-image.org/docs/stable/api/skimage.measure.html#skimage.measure.regionprops

                min_row, min_col, max_row, max_col = obj["bbox"]
                if min_row > roi[0] and max_row < roi[1]:  # bbox inside the roi
                    frame_detected.append(f)
                    x_coord, y_coord = get_obj_pos(obj)

            if check_centroid:
                c_row, c_col = obj["centroid"][0]
                if roi[0] < c_row < roi[1]:  # centroid inside the roi
                    frame_detected.append(f)
                    x_coord, y_coord = get_obj_pos(obj)

        coordinates.append([x_coord, y_coord])

    return frame_detected, coordinates


# %%


def main():
    logging.basicConfig(level=logging.DEBUG, format="%(message)s")
    logging.getLogger("matplotlib").setLevel(logging.WARNING)
    logging.getLogger("skimage").setLevel(logging.WARNING)

    FILENAME = "8. pallet_jack_105deg.h5"
    FILEPATH = Path("/path/to/local/file/directory/")
    FP = Path.joinpath(FILEPATH, FILENAME)

    (
        data_2d_left,
        data_2d_right,
        data_3d_left,
        data_3d_right,
        data_ods,
    ) = get_data_from_h5(FP)
    distance_map, frames = get_distance_map_data(data_ods)

    # Plot the distance map
    plt.figure(100)
    plt.imshow(distance_map.T, cmap="jet", interpolation="none")
    plt.colorbar()
    plt.axhline(85, color="r", linestyle="dashed")
    plt.axhline(115, color="r", linestyle="dashed")
    plt.xlabel("Frame counter #frame")
    plt.ylabel("Y-coordinates in occ pixel space")
    plt.title("Distance Map of Recorded Data")

    # Plot a selection of occupancy grids before and after the detection
    plt.figure(200)
    range_occ_grids = np.arange(frames[0] - 8, frames[0] + 8)
    for i, frame in enumerate(range_occ_grids):

        plt.subplot(4, 4, i + 1)
        plt.imshow(data_ods[frame]["image"], cmap="gray", interpolation="none")
        plt.axhline(85, color="r", linestyle="dashed")
        plt.axhline(115, color="r", linestyle="dashed")
        plt.colorbar()
        if frame == frames[0]:
            plt.title(f"Object detected in frame {frame}")
        else:
            plt.title(f"Frame {frame}")

    # Distance Tracker
    frame_detected, coordinates = distance_tracker(data_ods, frames)
    trans_x, trans_y, trans_z = data_3d_right["extrinsicOpticToUserTrans"][
        0
    ]  # get extrinsic calibration values

    user_origin = [100, 100]
    trans_x_grid_space = (trans_x * 1000) / 50
    trans_y_grid_space = (trans_y * 1000) / 50

    distances = []
    for coord in coordinates:
        if coord[0] is not None:
            distances.append(
                math.sqrt(
                    (coord[0] - user_origin[0] - trans_y_grid_space) ** 2
                    + (coord[1] - user_origin[1] - trans_x_grid_space) ** 2
                )
            )

    distances = np.convolve(
        distances, np.ones(5) / 5, mode="valid"
    )  # smooth distance information

    plt.figure(301)
    for d, f in zip(distances, frame_detected):
        plt.plot(f, d * 50, "b+")
    plt.xlim(0, len(data_ods) + 1)
    plt.xlabel("frame counter")
    plt.ylabel("Distance in mm")
    dist_y_max = max(distances) * 50
    plt.title(
        f"detected object: distance tracking over time\n maximum distance: {int(dist_y_max)} mm"
    )

    plt.figure()
    pos = np.arange(130, 166)
    for n in range(len(pos)):
        plt.subplot(6, 6, n + 1)
        plt.imshow(data_ods[pos[n]]["image"] > 127,
                   cmap="gray", interpolation="none")
        try:
            idx = frame_detected.index(pos[n])
            plt.plot(coordinates[idx][1], coordinates[idx][0], "r+")
        except ValueError as e:
            pass
        plt.colorbar()
        plt.title(f"frame {pos[n]}")


if __name__ == "__main__":
    main()
# %%
