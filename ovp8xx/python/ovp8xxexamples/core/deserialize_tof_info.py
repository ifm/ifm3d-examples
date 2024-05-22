#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# This examples shows how to use the deserializer module
# to extract data from the TOFInfoV4 buffer.
#################################################################
# Import the relevant modules
from ifm3dpy.device import O3R
from ifm3dpy.framegrabber import FrameGrabber, buffer_id
from ifm3dpy.deserialize import TOFInfoV4

def main(IP:str , PORT:str) -> None:
    ###########################
    # Create the O3R and FrameGrabber
    # and choose which images to receive. 
    # In this example we only receive one frame.
    ###########################
    o3r = O3R(IP)
    # Assuming PORT is a 3D port
    pcic_port = o3r.port(PORT).pcic_port
    fg = FrameGrabber(cam=o3r, pcic_port=pcic_port)
    # Define the images to receive when starting the data stream
    fg.start([buffer_id.TOF_INFO])
    # Get a frame
    [ok, frame] = fg.wait_for_frame().wait_for(500)
    # Raise timeout error is not frame is received
    if not ok:
        raise TimeoutError("No frame received, make sure the camera is in RUN state")

    fg.stop()
    ###############################
    # Extract data from the buffer
    # Using the deserializer module
    ###############################
    tof_info = TOFInfoV4().deserialize(frame.get_buffer(buffer_id.TOF_INFO))
    print("Sample of data available in the TOFInfoV4 buffer:")
    print(f"Current minimum measurement range: {tof_info.measurement_range_min} m")
    print(f"Current maximum measurement range: {tof_info.measurement_range_max} m")
    print(f"Temperature of the illumination module: {tof_info.illu_temperature}")

if __name__ == "__main__":
    try:
        # If the example python package was build, import the configuration
        from ovp8xxexamples import config
        IP = config.IP
        PORT = config.PORT_3D
    except ImportError:
        # Otherwise, use default values
        print(
            "Unable to import the configuration.\nPlease run 'pip install -e .' from the python root directory"
        )
        print("Defaulting to the default configuration.")
        IP = "192.168.0.69"
        PORT = "port2"
    main(IP=IP, PORT=PORT)