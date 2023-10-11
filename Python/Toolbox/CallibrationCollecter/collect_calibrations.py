#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# %%
import logging
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import buffer_id, FrameGrabber
from ifm3dpy.deserialize import RGBInfoV1, TOFInfoV4

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG, format="%(message)s")


class PortCalibrationCollector:
    """
    Utilities for collecting and deserializing calibration data for a port.
    """

    def __init__(self, o3r, port_info):
        self.calibrations = {}
        self.port_info = port_info
        self.o3r = o3r
        self.frame_grabber = FrameGrabber(self.o3r, self.port_info.pcic_port)
        self.buffer_of_interest = {
            "3D": buffer_id.TOF_INFO,
            "2D": buffer_id.RGB_INFO,
        }[self.port_info.type]

    def collect(self) -> dict:
        """
        Collect and deserialize the calibration information for the 2D or 3D imager
        at the requested port.
        """
        self.o3r.set({"ports": {f"{self.port_info.port}": {"state": "RUN"}}})
        self.frame_grabber.start([self.buffer_of_interest])
        ret, frame = self.frame_grabber.wait_for_frame().wait_for(1000)
        if not ret:
            raise TimeoutError("No frame was collected.")
        buffer = frame.get_buffer(self.buffer_of_interest)

        if self.port_info.type == "2D":
            rgb_info = RGBInfoV1().deserialize(buffer)
            self.calibrations["ext_optic_to_user"] = rgb_info.extrinsic_optic_to_user
            self.calibrations["intrinsic_calibration"] = rgb_info.intrinsic_calibration
            self.calibrations[
                "inverse_intrinsic_calibration"
            ] = rgb_info.inverse_intrinsic_calibration

        if self.port_info.type == "3D":
            tof_info = TOFInfoV4().deserialize(buffer)
            self.calibrations["ext_optic_to_user"] = tof_info.extrinsic_optic_to_user
            self.calibrations["intrinsic_calibration"] = tof_info.intrinsic_calibration
            self.calibrations[
                "inverse_intrinsic_calibration"
            ] = tof_info.inverse_intrinsic_calibration

        self.frame_grabber.stop()
        del self.frame_grabber

        logger.info(f"Collected calibration data for port {self.port_info.port}.")
        return self.calibrations


if __name__ == "__main__":

    IP = "192.168.0.69"

    import argparse

    parser = argparse.ArgumentParser(
        description="ifm ods example",
    )
    parser.add_argument(
        "--IP", type=str, default="192.168.0.69", help="IP address to be used"
    )
    args = parser.parse_args()
    ADDR = args.IP
    o3r = O3R(IP)
    ports_calibs = {}
    try:
        for port in o3r.ports():
            if port.type != "IMU" and port.type != "app":
                ports_calibs[port.port] = PortCalibrationCollector(o3r, port).collect()
                # The logged messages illustrate how to access the calibration data
                # stored in the custom objects
                logger.info(f"Sample of the extrinsic optics to user for {port.port}: ")
                logger.info(
                    f"rot_x: {ports_calibs[port.port]['ext_optic_to_user'].rot_x}"
                )
                logger.info(
                    f"trans_x: {ports_calibs[port.port]['ext_optic_to_user'].trans_x}"
                )

                logger.info(f"Sample of the intrinsics for {port.port}: ")
                logger.info(
                    f"Model id: {ports_calibs[port.port]['intrinsic_calibration'].model_id}"
                )
                logger.info(
                    f"Parameter [0]: {ports_calibs[port.port]['intrinsic_calibration'].parameters[0]}"
                )

                logger.info(f"Sample of the inverse intrinsics for {port.port}: ")
                logger.info(
                    f"Model id: {ports_calibs[port.port]['inverse_intrinsic_calibration'].model_id}"
                )
                logger.info(
                    f"Parameter [0]: {ports_calibs[port.port]['inverse_intrinsic_calibration'].parameters[0]}"
                )

    except Exception as e:
        logger.info(e)


# %%
