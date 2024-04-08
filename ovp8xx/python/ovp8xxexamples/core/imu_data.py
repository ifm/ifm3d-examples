from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id
from imu_deserializer import IMUOutput
import json

def main(ip, port):
    # Initialize the objects
    o3r = O3R(ip)
    pcic_port = o3r.port(port).pcic_port
    fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)

    # Change port to RUN state
    config = o3r.get()
    if config["ports"][port]["state"] != "RUN":
        raise RuntimeError(f'"Cannot receive data from IMU. IMU state: {config["ports"][port]["state"]}"')

    # Start the Framegrabber
    fg.start()

    while True:
        try:
            [ok, frame] = fg.wait_for_frame().wait_for(500)
            assert ok, "Timeout while waiting for a frame."

            imu_data_raw = frame.get_buffer(buffer_id.O3R_RESULT_IMU)
            imu_data = IMUOutput.parse(
                imu_data_raw.tobytes()
            )  # at the moment ifm3dpy only pass the raw data from the pcic port
            print(f'IMU version: {imu_data.imu_version}')
            print(f'Number of Samples: {imu_data.num_samples}')
            for i in range(len(imu_data.imu_samples)):
                print(f'Sample {i}: {imu_data.imu_samples[i]} \n')
            print(f'Extrinsic IMU to User: \n rot_x: {imu_data.extrinsic_imu_to_user.rot_x} \n rot_y: {imu_data.extrinsic_imu_to_user.rot_y} \n rot_z: {imu_data.extrinsic_imu_to_user.rot_z} \n trans_x: {imu_data.extrinsic_imu_to_user.trans_x} \n trans_y: {imu_data.extrinsic_imu_to_user.trans_y} \n trans_z: {imu_data.extrinsic_imu_to_user.trans_z} \n ')

            print(f'Extrinsic IMU to VPU: \n rot_x: {imu_data.extrinsic_imu_to_vpu.rot_x} \n rot_y: {imu_data.extrinsic_imu_to_vpu.rot_y} \n rot_z: {imu_data.extrinsic_imu_to_vpu.rot_z} \n trans_x: {imu_data.extrinsic_imu_to_vpu.trans_x} \n trans_y: {imu_data.extrinsic_imu_to_vpu.trans_y} \n trans_z: {imu_data.extrinsic_imu_to_vpu.trans_z} \n ')
            print(f'Receive Timestamp: {imu_data.imu_fifo_rcv_timestamp}')

        except KeyboardInterrupt:
            # Stop the streaming
            fg.stop().wait()
            break

if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config
        IP = config.IP
        PORT = config.PORT_IMU
    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        PORT = "port6"

    main(ip=IP, port=PORT)
