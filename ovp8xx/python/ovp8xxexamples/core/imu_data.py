#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# Example script to receive the data from IMU
# %%
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id
from imu_deserializer import IMUOutput
# %%


def main(ip: str):
    """ Receive the IMU data

    Args:
        ip (str): IP address of the VPU
    """
    # Initialize the objects
    o3r = O3R(ip)
    # IMU is always mapped to the virtual port ``
    port = 'port6'
    pcic_port = o3r.get(["/ports/port6/data/pcicTCPPort"]
                        )["ports"]["port6"]["data"]["pcicTCPPort"]
    fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)

    # Check the port state and change to RUN if it is not
    config = o3r.get(["/ports/port6/state"])
    if config["ports"][port]["state"] != "RUN":
        print(
            f'Change the port state from {config["ports"][port]["state"]} to RUN')
        o3r.set({"ports": {port: {"state": "RUN"}}})

    # Start the Framegrabber
    fg.start()

    try:
        [ok, frame] = fg.wait_for_frame().wait_for(500)
        assert ok, "Timeout while waiting for a frame."

        imu_data_raw = frame.get_buffer(buffer_id.O3R_RESULT_IMU)
        # at the moment ifm3dpy only pass the raw data from the pcic port
        imu_data = IMUOutput.parse(imu_data_raw)
        print(f'IMU version: {imu_data.imu_version}')
        print(f'Number of Samples: {imu_data.num_samples}')

        for i in range(len(imu_data.imu_samples)):
            print(f'Sample {i}: {imu_data.imu_samples[i]} \n')

        print(f'Extrinsic IMU to User: \n rot_x: {imu_data.extrinsic_imu_to_user.rot_x} \n rot_y: {imu_data.extrinsic_imu_to_user.rot_y} \n rot_z: {imu_data.extrinsic_imu_to_user.rot_z} \n trans_x: {imu_data.extrinsic_imu_to_user.trans_x} \n trans_y: {imu_data.extrinsic_imu_to_user.trans_y} \n trans_z: {imu_data.extrinsic_imu_to_user.trans_z} \n ')

        print(f'Extrinsic IMU to VPU: \n rot_x: {imu_data.extrinsic_imu_to_vpu.rot_x} \n rot_y: {imu_data.extrinsic_imu_to_vpu.rot_y} \n rot_z: {imu_data.extrinsic_imu_to_vpu.rot_z} \n trans_x: {imu_data.extrinsic_imu_to_vpu.trans_x} \n trans_y: {imu_data.extrinsic_imu_to_vpu.trans_y} \n trans_z: {imu_data.extrinsic_imu_to_vpu.trans_z} \n ')
        print(f'Receive Timestamp: {imu_data.imu_fifo_rcv_timestamp}')

        fg.stop().wait()

    except AssertionError:
        # Stop the streaming
        fg.stop().wait()


if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config
        IP = config.IP

    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"

    main(ip=IP)
