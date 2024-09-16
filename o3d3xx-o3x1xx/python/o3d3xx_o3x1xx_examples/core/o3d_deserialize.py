#!/usr/bin/env python3
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This examples shows how to use the
# deserializer modules to extract data from
# the O3D frame
#############################################
# Import the relevant modules and configure
# the logger
import logging
from ifm3dpy.device import O3D
from ifm3dpy.framegrabber import FrameGrabber, buffer_id, Frame
from ifm3dpy.deserialize import (
    ExtrinsicOpticToUser,
    O3DExposureTimes,
    O3DILLUTemperature,
    O3DExtrinsicCalibration,
    O3DInstrinsicCalibration,
    O3DInverseInstrinsicCalibration,
)


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(message)s")
#################################################################


# Define a function to extract the data from the frame
def extract_data(
    frame: Frame,
) -> tuple[
    O3DExposureTimes,
    ExtrinsicOpticToUser,
    O3DInstrinsicCalibration,
    O3DInverseInstrinsicCalibration,
    O3DILLUTemperature,
]:
    """Extract the data from the frame object

    Args:
        frame (_type_): ifm3d frame object
    """
    # Get buffers from frame object for deserialization
    if frame is not None:
        exposure_times_buffer = frame.get_buffer(buffer_id.EXPOSURE_TIME)
        exposure_times = O3DExposureTimes().deserialize(exposure_times_buffer)

        extrinsic_calib_buffer = frame.get_buffer(buffer_id.EXTRINSIC_CALIB)
        extrinsic_calib = O3DExtrinsicCalibration().deserialize(extrinsic_calib_buffer)

        intrinsic_calib_buffer = frame.get_buffer(buffer_id.INTRINSIC_CALIB)
        intrinsic_calib = O3DInstrinsicCalibration().deserialize(intrinsic_calib_buffer)

        inv_intrinsic_calib_buffer = frame.get_buffer(
            buffer_id.INVERSE_INTRINSIC_CALIBRATION
        )
        inv_intrinsic_calib = O3DInverseInstrinsicCalibration().deserialize(
            inv_intrinsic_calib_buffer
        )

        illumination_temperature_buffer = frame.get_buffer(buffer_id.ILLUMINATION_TEMP)
        illumination_temperature = O3DILLUTemperature().deserialize(
            illumination_temperature_buffer
        )

        return (
            exposure_times,
            extrinsic_calib,
            intrinsic_calib,
            inv_intrinsic_calib,
            illumination_temperature,
        )
    raise RuntimeError("Empty frame object")


def main(IP: str) -> None:
    ###########################
    # Create the O3D and FrameGrabber
    # and choose which images to receive.
    # In this example we only receive one frame.
    ###########################
    o3d = O3D(IP)

    pcic_port = int(o3d.device_parameter("PcicTcpPort"))
    fg = FrameGrabber(cam=o3d, pcic_port=pcic_port)

    # Define the images to receive when starting the data stream
    fg.start(
        [
            buffer_id.EXPOSURE_TIME,
            buffer_id.EXTRINSIC_CALIB,
            buffer_id.INTRINSIC_CALIB,
            buffer_id.INVERSE_INTRINSIC_CALIBRATION,
            buffer_id.ILLUMINATION_TEMP,
        ]
    )

    trigger_mode = o3d.to_json()["ifm3d"]["Apps"][0]["TriggerMode"]

    if trigger_mode == "1":
        logger.info("Camera is in Continuous Trigger Mode")
    elif trigger_mode == "2":
        logger.info("Camera is in Software Trigger Mode")
        # Software Trigger the camera
        fg.sw_trigger()

    # Get a frame
    [ok, frame] = fg.wait_for_frame().wait_for(1500)  # wait with 1500ms timeout

    # Check that a frame was received
    if not ok:
        raise RuntimeError("Timeout while waiting for a frame.")
    ###############################
    # Extract data from the buffer
    # and print the data
    ###############################
    (
        exposure_times,
        extrinsic_calib,
        intrinsic_calib,
        inv_intrinsic_calib,
        illu_temp,
    ) = extract_data(frame=frame)
    logger.info(f"Exposure Time: {exposure_times.data}")
    logger.info(
        f"Extrinsic Calibration [trans_x, trans_y, trans_z, rot_x, rot_y, rot_z]: {extrinsic_calib}"
    )
    logger.info(f"Intrinsic Calibration: {intrinsic_calib}")
    logger.info(f"Inverse Intrinsic Calibration: {inv_intrinsic_calib}")
    logger.info(f"Illumination Temperature: {illu_temp.data}")

    fg.stop()


if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from o3d3xx_o3x1xx_examples import config

        IP = config.IP
    except ImportError:
        # Otherwise, use default values
        logger.warning(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        logger.warning("Defaulting to the default configuration.")
        IP = "192.168.0.70"

    main(IP=IP)
