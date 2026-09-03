# -*- coding: utf-8 -*-
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# Example script to receive the data from IMU
# The IMUInfoV1 is available from ifm3dpy >= 1.6.15 and firmware version 1.4.30 or higher.
# For the legacy IMU data structure, please refer to the https://github.com/ifm/ifm3d-examples/blob/v1.4.0/ovp8xx/python/core/imu_data.py.

from ifm3dpy.deserialize import IMUInfoV1
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


def main(ip: str) -> None:
    """Receive the IMU data

    Args:
        ip (str): IP address of the VPU
    """
    # Initialize the objects
    o3r = O3R(ip)

    # PORT IMU is fixed to port6
    pcic_port = o3r.port("port6").pcic_port
    fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)

    # Check the port state and change to RUN if it is not
    config = o3r.get(["/ports/port6/state"])
    if config["ports"]["port6"]["state"] != "RUN":
        print(f'Change the port state from {config["ports"]["port6"]["state"]} to RUN')
        o3r.set({"ports": {"port6": {"state": "RUN"}}})

    # Start the Framegrabber
    fg.start([buffer_id.O3R_RESULT_IMU])
    [ok, frame] = fg.wait_for_frame().wait_for(500)

    if not ok:
        fg.stop().wait(500)
        raise TimeoutError("Failed to receive IMU frame within the timeout period.")

    # Deserialize the IMU data and print it
    imu_data = IMUInfoV1.deserialize(frame.get_buffer(buffer_id.O3R_RESULT_IMU))

    print(f"IMU version: {imu_data.imu_version}\n")
    print(f"Number of Samples: {imu_data.num_samples}\n")
    print(f"Receive Timestamp: {imu_data.imu_fifo_rcv_timestamp}\n")
    print(
        f"Extrinsic IMU to User: \n \
            rot_x: {imu_data.extrinsic_imu_to_user.rot_x}\n \
            rot_y: {imu_data.extrinsic_imu_to_user.rot_y}\n \
            rot_z: {imu_data.extrinsic_imu_to_user.rot_z}\n \
            trans_x: {imu_data.extrinsic_imu_to_user.trans_x}\n \
            trans_y: {imu_data.extrinsic_imu_to_user.trans_y}\n \
            trans_z: {imu_data.extrinsic_imu_to_user.trans_z}\n"
    )

    # A single IMU frame contains multiple samples. This is due to
    # the fact that the framerate of the IMU is greater than the
    # rate at which we poll the data. Each sample will be similarly structured.
    sample = imu_data.imu_samples[0]
    print(
        f"First IMU Sample: \n \
          HW Timestamp: {sample.hw_timestamp} \n \
          Timestamp: {sample.timestamp} \n \
          Temperature: {sample.temperature} \n \
          Acceleration X: {sample.acc_x} \n \
          Acceleration Y: {sample.acc_y} \n \
          Acceleration Z: {sample.acc_z} \n \
          Gyro X: {sample.gyro_x} \n \
          Gyro Y: {sample.gyro_y} \n \
          Gyro Z: {sample.gyro_z} \n"
    )
    fg.stop().wait()


if __name__ == "__main__":
    IP = "192.168.0.69"
    main(ip=IP)
