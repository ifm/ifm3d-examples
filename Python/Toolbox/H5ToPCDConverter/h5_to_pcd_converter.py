#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This example shows how to unpack data saved
# in the ifm h5 format (for example with the
# ifm Vision Assistant) into .pcd files. One
# file per recorded frame is created.

# Record data with the iVA. If you do not record
# the point cloud along with the rest of the data,
# we will attempt to calculate it in this script.
# If the necessary imported functions are not
# available, an error will be raised.

# %%
from pathlib import Path
from dataclasses import dataclass
from os.path import join as path_join
import argparse
import logging
import numpy as np
import h5py
import open3d

# Optional import of utilities from another example.
# This is used in cases where the point cloud data is
# not available in the HDF5 dataset.
# If the module is not found, the point cloud cannot
# be calculated from the radial distance image.
try:
    import sys
    import os

    sys.path.append(os.path.dirname(os.getcwd()) + "/Registration2d3d")
    from transforms import intrinsic_projection

    transforms_available = True
except ModuleNotFoundError:
    transforms_available = False

status_logger = logging.getLogger(__name__)

# %%


@dataclass
class TOFData:
    """
    This data class mirrors how data is formatted
    in the ifm HDF5 format as saved in iVA recordings
    and provides utilities to convert to pcd format.
    """

    dis: np.ndarray
    amp: np.ndarray
    width: np.uint16
    height: np.uint16
    frameCounter: np.uint32
    distanceResolution: np.float32
    amplitudeResolution: np.float32
    modelID3D: np.uint32
    intrinsics3: np.ndarray
    inv_intrinsic3: np.ndarray
    extrinsic3D: np.ndarray
    cloud: np.ndarray
    cloud_data: bool

    def pcd_from_numpy_array(self):
        """Format the point cloud to the pcd format.

        :return: formatted cloud
        """
        array = self.cloud
        height = self.dis.shape[0]
        width = self.dis.shape[1]

        pcd = open3d.geometry.PointCloud()
        xyz = np.reshape(array, (3, height * width))
        xyz = np.transpose(xyz)
        pcd.points = open3d.utility.Vector3dVector(xyz)

        return pcd

    def calc_pointcloud(self):
        """Calculate the point cloud from the radial
        distance image in cases where the point cloud
        was not saved in the HDF5 dataset.

        :return: point cloud
        """
        # Calculate 3D unit vectors corresponding to each pixel
        # of depth camera
        ux, uy, uz = intrinsic_projection(
            self.modelID3D, self.intrinsics3, *self.dis.shape[::-1]
        )

        # Multiply unit vectors by depth of corresponding pixel
        x = (ux * self.dis).flatten()
        y = (uy * self.dis).flatten()
        z = (uz * self.dis).flatten()
        valid = self.dis.flatten() > 0.05

        status_logger.info(f"{round(sum(valid)/x.size*100)}% valid pts")
        for i, pt_valid in enumerate(valid):
            if not pt_valid:
                x[i] = y[i] = z[i] = 0.0

        # Restructure point cloud as sequence of points
        pcd_o3 = np.stack((x, y, z), axis=0)

        return pcd_o3


# %%


def load_o3r_tof_h5(filename: str) -> list:
    """load data: ifm h5 data container - e.g. recording from ifm Vision Assistant

    :param filename (str): filename
    :raises ValueError: if missing data in file
    :return list: list of data classes
    """

    hf1 = h5py.File(filename, "r")
    status_logger.info(f"data file loaded: {filename}")

    # list all available data keys
    # hf1["streams"]["o3r_tof_0"][0].dtype

    def load_tof_stream_data(tof_stream_name: str, cloud_data=True) -> dict:
        """Get the point cloud data for a specific tof data stream.

        :param tof_stream_name: tof stream name in recording.
        :param cloud_data: availability of cloud data, defaults to True
        :raises Exception: if no point cloud data is available and
                            it cannot be calculated dut to missing imports.
        :return: data including point cloud.
        """
        data = []

        try:
            _ = hf1["streams"][tof_stream_name][0]["cloud"]
            cloud_data = True
        except ValueError as e:
            cloud_data = False
            status_logger.error(f"No 3D data available in {tof_stream_name}")
            # raise e

        for d in hf1["streams"][tof_stream_name]:
            extrinsic3D = d["extrinsicOpticToUserTrans"]
            extrinsic3D = np.append(extrinsic3D, d["extrinsicOpticToUserRot"])
            tof_data = TOFData(
                amp=d["amplitude"],
                dis=d["distance"],
                amplitudeResolution=d["amplitudeResolution"],
                distanceResolution=d["distanceResolution"],
                extrinsic3D=extrinsic3D,
                cloud=[],
                frameCounter=d["frameCounter"],
                height=d["height"],
                intrinsics3=d["intrinsicCalibModelParameters"],
                inv_intrinsic3=d["invIntrinsicCalibModelParameters"],
                modelID3D=d["intrinsicCalibModelID"],
                width=d["width"],
                cloud_data=cloud_data,
            )

            if cloud_data:
                tof_data.cloud = d["cloud"]
            else:
                if transforms_available:
                    tof_data.cloud = tof_data.calc_pointcloud()
                else:
                    tof_data.cloud = np.zeros((tof_data.width, tof_data.height, 3))
                    cloud_data = False
                    raise Exception(
                        "Cannot calculate the point cloud due to missing transforms package."
                    )

            data.append(tof_data)

        return {"tof_stream": tof_stream_name, "data": data}

    tof_data = []
    tof_stream_names = [
        streams for streams in list(hf1["streams"]) if "o3r_tof" in streams
    ]

    for tof_stream_name in tof_stream_names:
        tof_data.append(load_tof_stream_data(tof_stream_name=tof_stream_name))

    hf1.close()
    return tof_data


def visualize_pcd(path_to_pcd: str) -> None:
    pcd = open3d.io.read_point_cloud(path_to_pcd, format="pcd")
    if len(pcd.points) == 0:
        raise Exception("No point cloud data, possibly wrong path provided")
    open3d.visualization.draw_geometries([pcd])


def safe_pcd_file(pcd: open3d.cpu.pybind.geometry.PointCloud, filename: str) -> bool:
    try:
        open3d.io.write_point_cloud(filename, pcd)
        return True
    except Exception as e:
        status_logger.error(e)
        return False


# %%


def main(filename):
    data = load_o3r_tof_h5(filename=filename)
    parent_file_name = filename.split(".")[0]
    directory = Path(filename).parent.resolve()

    status_logger.info(f"parent filename: {parent_file_name}")
    status_logger.info(f"saving directory: {directory}")

    for tof_stream in data:
        tof_stream_data = tof_stream["data"]
        tof_stream_name = tof_stream["tof_stream"]

        for d in tof_stream_data:
            pcd = d.pcd_from_numpy_array()

            filename = "".join(
                [
                    parent_file_name,
                    "_",
                    tof_stream_name,
                    "_",
                    str(d.frameCounter),
                    ".pcd",
                ]
            )
            directory_filename = path_join(directory, filename)

            status_logger.info(
                f"data converted to PCD: start saving the data to file {filename}"
            )

            safe_pcd_file(filename=directory_filename, pcd=pcd)
        status_logger.info("finished converting")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="H5ToPCDConverter",
        description="converts ifm HDf5 data files to PCD files",
    )
    parser.add_argument("--filename", default="test_rec.h5")

    args = parser.parse_args()
    main(args.filename)

# %%
