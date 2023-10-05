#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

#%%
import ifm3dpy
from ifm3dpy import buffer_id, FrameGrabber, O3R
import logging

import struct
from pprint import pprint

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(message)s")

class PortCalibrationCollector:
    def __init__(self, o3r, port_n: int, port_config: dict=None, timeout=0.25):

        self.ifm3dpy_v = [int(v) for v in ifm3dpy.__version__.split(".")]
        if not (self.ifm3dpy_v[0]==1 and self.ifm3dpy_v[1] in [0,1]):
            raise RuntimeError(f'unsupported ifm3dpy version: v{self.ifm3dpy_v}')

        self.calibrations = None
        self.port_n = port_n
        self.port_config = port_config
        self.sensor_type = port_config["info"]["features"]["type"]
        self.o3r = o3r

        self._prepare_buffers()
        self._prepare_cam()
        self.collect()
        # _restore_cam_config()


    def collect(self):
        """collect one set of calibration data per imager
        """
        ret, self.frame = self.frame_grabber.wait_for_frame().wait_for(10000)
        self.buffers = {
            buffer_of_interest: self.frame.get_buffer(buffer)
            for buffer_of_interest, buffer in self.buffers_of_interest.items()
        }

        if self.sensor_type == "2D":
            self._get_2D_calibration()

        if self.sensor_type == "3D":
            self._get_3D_calibration()

        self.release_fgs()
        logger.info(f"Collected calibration data for port {self.port_n}.")

    def release_fgs(self):
        self.frame_grabber.stop()
        del self.frame_grabber

    def _restore_cam_config(self):
        """restore cam configuration before data retrieval
        """
        # restore original port configuration
        self.o3r.set({"ports": {f"port{self.port_n}": self.port_config}})

    def _prepare_cam(self):
        """prepare cams / imagers for data retrieval
        """
        camera_run_config = {"ports": {f"port{self.port_n}": {"state": "RUN"}}}
        self.o3r.set(camera_run_config)
        self.frame_grabber = FrameGrabber(self.o3r, 50010 + self.port_n)
        self.frame_grabber.start(list(self.buffers_of_interest.values()))

    def _prepare_buffers(self):
        """prepare data structure
        """
        self.buffers_of_interest = {
            "3D": {
                "ext_optic_to_user": buffer_id.EXTRINSIC_CALIB,
                "intrinsic_calibration": buffer_id.INTRINSIC_CALIB,
                "inverse_intrinsic_calibration": buffer_id.INVERSE_INTRINSIC_CALIBRATION,
            },
            "2D": {"rgb_image_info": buffer_id.O3R_RGB_IMAGE_INFO},
        }[self.sensor_type]

    def _get_3D_calibration(self):
        """parse 3D calibration data structures
        """
        self.calibrations = self.buffers
            # parameter_name, format,
        deserialization_schema = [
                ("intrinsic_calibration", "<I32f"),
                ("inverse_intrinsic_calibration", "<I32f"),
            ]
        for parameter_name, frmt in deserialization_schema:
            value = struct.unpack(
                    frmt, self.calibrations[parameter_name].tobytes()
                )
            if len(value) > 11:
                value = value[:11]
            self.calibrations[parameter_name] = value
        self.calibrations["ext_optic_to_user"] = tuple(self.calibrations["ext_optic_to_user"].tolist()[0])

    def _get_2D_calibration(self):
        """parse 2D calibration data structure
        """
        raw_buffer_data = self.buffers["rgb_image_info"][0]
        # parameter_name, format, offset, n_bits,
        deserialization_schema = [
            # ("version", "<I", 0, 4),
            # ("frameCounter", "<I", 4, 4),
            # ("timestamp_ns", "<Q", 8, 8),
            # ("exposureTime", "<I", 16, 4),
            ("ext_optic_to_user", "<6f", 20, 24),
            ("intrinsic_calibration", "<I32f", 44, 132),
            ("inverse_intrinsic_calibration", "<I32f", 44 + 132, 132),
        ]
        self.calibrations = {}
        for parameter_name, frmt, offset, n_bytes in deserialization_schema:
            value = struct.unpack(
                frmt, raw_buffer_data[offset : offset + n_bytes].tobytes()
            )
            if len(value) == 1:
                value = value[0]
            elif len(value) > 11:
                value = value[:11]
            self.calibrations[parameter_name] = value

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--IP", nargs="?", default = "192.168.0.69")
    args = parser.parse_args()

    IP_ADDR = args.IP
    logger.info(f"Connecting to {IP_ADDR}")

    o3r = O3R(IP_ADDR)
    try:
        port_config = o3r.get(["/ports"])
    except Exception as e:
        logger.info(f"No VPU found at {IP_ADDR}. Can you ping the sensor?")
        logger.info(e)
        exit()

    port_names = port_config["ports"]

    port_names_sans_imu={}
    for name,config in port_names.items():
        if "6" not in name:
            port_names_sans_imu[name]=config

    port_handles = {
        int(port_n[-1]): PortCalibrationCollector(o3r, int(port_n[-1]), port_config)
        for port_n, port_config in port_names_sans_imu.items()
    }

    for port_n, port_handle in port_handles.items():
        logger.info(f"\nPort {port_n} calibrations:")
        pprint(port_handle.calibrations)


# %%
