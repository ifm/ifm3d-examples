# Core
In this directory you find multiple general O3R scripts that are explained below:

## 2D data
Receiving RGB data with `ifm3dpy` is done similarly as 3D data: the core objects have to be instantiated, and a frame has to be retrieved. 
The important part is how to access the RGB image and how to decode it for further use.
Once decoded, the image can be displayed using tools such as OpenCV. The example code in `2d_data.py` illustrates the explained process.


## Configuration

The O3R has multiple parameters that have an influence on the point cloud. Some of them affect the raw measurement and others modify how the data is converted into x,y,z, etc values. These parameters can be changed to better fit your applications and the script `configuration.py` presents how. You can refer to [this page](https://ifm3d.com/latest/Technology/3D/index_3d.html) for a detailed description of each parameter.

The ifm3d API provides functions to read and set the configuration of the device. Note that JSON formatting is used for all the configurations.

## Deserialization

Some of the data provided by the O3R platform needs to be deserialized to be used. This is the case for:
- the intrinsic calibration parameters (`ifm3dpy.deserialize.Calibration`), which provides details like which optical model is used (Fisheye, pinhole) and the values for each of the model's parameters,
- the extrinsic calibration (optics to user) parameters (` ifm3dpy.deserialize.ExtrinsicOpticToUser`), which provides the transformations between the optical system and the reference point on the camera housing,
- the ODS zone information (`ifm3dpy.deserialize.ODSInfoV1`), which contains the zone id being used and the occupancy of the zones,
- the ODS occupancy grid information (`ifm3dpy.deserialize.ODSOccupancyGridV1`), which contains occupancy grid data and the transformation matrix,
- the RGB information (`ifm3dpy.deserialize.RGBInfoV1`), which provides exposure times and calibration parameters for the O3R RGB cameras.

For more information on the data structures of each buffer please refer to the [python3 API documentation](https://api.ifm3d.com/latest/_autosummary/ifm3dpy.deserialize.html).

The usage of the deserializer is the same for all the buffers mentioned above: create the object, and call the deserialize function. Follow the example code, `deserialize.py` for an example on deserializing the `RGBInfoV1` buffer.

## Getting data

The primary objective of `ifm3d` is to make it as simple and performant as possible to acquire pixel data from an ifm 3D camera of the O3xxxx series.
Additionally, the data should be encoded in a useful format for performing computer vision and/or robotics perception tasks.
A typical `ifm3d` client program follows the structure of a control loop whereby images are continuously acquired from the camera and acted upon in some application-specific way.

`ifm3dpy` provides three main classes:
- `O3R` holds the configuration of the camera heads, handles the connection, etc;
- `FrameGrabber` receives frames (images);
- `Frame` stores the image buffers.

The `O3R` class, counter-intuitively, refers to the computing unit (the VPU). It inherits its name from previous ifm 3D devices that only used one camera, with no distinction between sensing and computing units.

The `FrameGrabber` stores a reference to the passed in camera shared pointer and starts a worker thread to stream in pixel data from the device.
Its inputs:
- `o3r`: The o3r instance (the image processing platform) that handles the connection the the camera heads;
- `port`: PCIC port number of the camera head to grab data from (not the physical port number);

Accessing the received data is done through the `Frame`. Different data types are available depending on whether the camera is a 2D or a 3D camera.
Simply access the image by calling `get_buffer` passing the `buffer_id` of the required image as a parameter.

The recommended way to receive a frame is to use the callback function, as shown in the `getting_data_callback.py` script. You can register a callback function that will be executed for every received frame, until the program exits. Alternatively, wait for a frame: you just need to call the `WaitForFrame` function, as shown in the `getting_data.py` script. 

## Multi head
The "multi_head.py" script demonstrates how to know the connected heads to the VPU and their types. 

## Viewer
In the `ifm3dpy_viewer.py` python3 script a full demonstration of how to view the different images is done.

## Firmware update

The script `fw_update_utils.py` demonstrates how to perform a firmware update for your O3R system. Additionally, the script includes several utility functions that provide information, such as determining the current firmware version.

## Timestamps

The script `timestamps.py` demonstrate how to get the timestamps and the effect of `sNTP` on the timestamps.

## Diagnostic
The script `diagnostic.py` contains helper functions for retrieving diagnostics when requested or asynchronously.

## Bootup monitor:
The script `bootup_monitor.py` checks that the VPU completes it's boot sequence before attempting to initialize an application.
