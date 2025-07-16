# -*- coding: utf-8 -*-
#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# Example script to receive the data from IMU
# The IMU data can only be accessed with firmware
# versions 1.4.X or higher, and ifm3d version
# 1.5.X or higher.

from deserialize_imu import IMUOutput
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id


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
    # ifm3dpy only provides the raw data from the IMU. The user
    # has to deserialize the data to retrieve the content.
    # We rely on the deserializer implemented in the
    # deserialize_imu.py script.
    imu_data = IMUOutput.parse(imu_data_raw)
    print(f"IMU version: {imu_data.imu_version}\n")
    print(f"Number of Samples: {imu_data.num_samples}\n")
    # A single IMU frame contains multiple samples. This is due to
    # the fact that the framerate of the IMU is greater than the
    # rate at which we poll the data. Each sample will be similarly structured.
    print("First sample:")
    print(f"    Hardware timestamp: {imu_data.imu_samples[0].hw_timestamp}")
    print(f"    Acquisition timestamp: {imu_data.imu_samples[0].timestamp}")
    print(f"    Temperature: {imu_data.imu_samples[0].temperature}")
    print(
        f"    Acceleration [m/s²]: \n        x: {imu_data.imu_samples[0].accel_x} \n        y: {imu_data.imu_samples[0].accel_y} "
        f"\n        z: {imu_data.imu_samples[0].accel_z}"
    )
    print(
        f"    Angular rate [rad/s] \n        x: {imu_data.imu_samples[0].gyro_x} \n        y: {imu_data.imu_samples[0].gyro_y} "
        f"\n        z: {imu_data.imu_samples[0].gyro_z}\n"
    )
    print(
        f"Extrinsic IMU to User: \n rot_x: {imu_data.extrinsic_imu_to_user.rot_x} \n rot_y: {imu_data.extrinsic_imu_to_user.rot_y} "
        f"\n rot_z: {imu_data.extrinsic_imu_to_user.rot_z} \n trans_x: {imu_data.extrinsic_imu_to_user.trans_x} "
        f"\n trans_y: {imu_data.extrinsic_imu_to_user.trans_y} \n trans_z: {imu_data.extrinsic_imu_to_user.trans_z} \n"
    )
    print(
        f"Extrinsic IMU to VPU: \n rot_x: {imu_data.extrinsic_imu_to_vpu.rot_x} \n rot_y: {imu_data.extrinsic_imu_to_vpu.rot_y} "
        f"\n rot_z: {imu_data.extrinsic_imu_to_vpu.rot_z} \n trans_x: {imu_data.extrinsic_imu_to_vpu.trans_x} "
        f"\n trans_y: {imu_data.extrinsic_imu_to_vpu.trans_y} \n trans_z: {imu_data.extrinsic_imu_to_vpu.trans_z} \n"
    )
    print(f"Receive Timestamp: {imu_data.imu_fifo_rcv_timestamp}")

    fg.stop().wait()


if __name__ == "__main__":
    IP = "192.168.0.69"
    PORT_IMU = "port6"
    main(ip=IP, port_imu=PORT_IMU)
