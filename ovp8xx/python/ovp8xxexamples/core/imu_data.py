#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# Example script to receive the data from IMU
# %%
import logging

from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id

try:
    from ovp8xxexamples.core.deserialize_imu import IMUOutput
except ImportError:
    print("Unable to import the IMUOutput class from the ovp8xxexamples package.")
    print("Please run 'pip install -e .' from the python root directory.")
    print("Defaulting to the local import.")
    from deserialize_imu import IMUOutput
# %%
logger = logging.getLogger(__name__)


def main(ip: str, port_imu: str):
    """Receive the IMU data

    Args:
        ip (str): IP address of the VPU
        port_imu (str): Port number of the IMU
    """
    # Initialize the objects
    o3r = O3R(ip)
    pcic_port = o3r.port(port_imu).pcic_port
    fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)

    # Check the port state and change to RUN if it is not
    config = o3r.get(["/ports/port6/state"])
    if config["ports"][port_imu]["state"] != "RUN":
        print(f'Change the port state from {config["ports"][port_imu]["state"]} to RUN')
        o3r.set({"ports": {port_imu: {"state": "RUN"}}})

    # Start the Framegrabber
    fg.start()
    [ok, frame] = fg.wait_for_frame().wait_for(500)

    if not ok:
        fg.stop().wait()
        raise TimeoutError("...")

    imu_data_raw = frame.get_buffer(buffer_id.O3R_RESULT_IMU)
    # at the moment ifm3dpy only pass the raw data from the pcic port
    imu_data = IMUOutput.parse(imu_data_raw)
    logger.info(f"IMU version: {imu_data.imu_version}\n")
    logger.info(f"Number of Samples: {imu_data.num_samples}\n")
    logger.info(f"First sample:")
    logger.info(f"    Hardware timestamp: {imu_data.imu_samples[0].hw_timestamp}")
    logger.info(f"    Acquisition timestamp: {imu_data.imu_samples[0].timestamp}")
    logger.info(f"    Temperature: {imu_data.imu_samples[0].temperature}")
    logger.info(
        f"    Acceleration: \n        x: {imu_data.imu_samples[0].accel_x} \n        y: {imu_data.imu_samples[0].accel_y} \n        z: {imu_data.imu_samples[0].accel_z}"
    )
    logger.info(
        f"    Gyroscope: \n        x: {imu_data.imu_samples[0].gyro_x} \n        y: {imu_data.imu_samples[0].gyro_y} \n        z: {imu_data.imu_samples[0].gyro_z}\n"
    )
    logger.info(
        f"Extrinsic IMU to User: \n rot_x: {imu_data.extrinsic_imu_to_user.rot_x} \n rot_y: {imu_data.extrinsic_imu_to_user.rot_y} \n rot_z: {imu_data.extrinsic_imu_to_user.rot_z} \n trans_x: {imu_data.extrinsic_imu_to_user.trans_x} \n trans_y: {imu_data.extrinsic_imu_to_user.trans_y} \n trans_z: {imu_data.extrinsic_imu_to_user.trans_z} \n "
    )
    logger.info(
        f"Extrinsic IMU to VPU: \n rot_x: {imu_data.extrinsic_imu_to_vpu.rot_x} \n rot_y: {imu_data.extrinsic_imu_to_vpu.rot_y} \n rot_z: {imu_data.extrinsic_imu_to_vpu.rot_z} \n trans_x: {imu_data.extrinsic_imu_to_vpu.trans_x} \n trans_y: {imu_data.extrinsic_imu_to_vpu.trans_y} \n trans_z: {imu_data.extrinsic_imu_to_vpu.trans_z} \n "
    )
    logger.info(f"Receive Timestamp: {imu_data.imu_fifo_rcv_timestamp}")

    fg.stop().wait()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config

        IP = config.IP
        PORT_IMU = config.PORT_IMU

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        PORT_IMU = "port6"

    main(ip=IP, port_imu=PORT_IMU)
