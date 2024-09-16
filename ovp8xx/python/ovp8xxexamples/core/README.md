# Core
In this directory you find multiple general O3R scripts that are explained below.

## `2d_data.py`
Receiving RGB data with `ifm3dpy` is done similarly as 3D data: the core objects have to be instantiated, and a frame has to be retrieved. 
The important part is how to access the RGB image and how to decode it for further use.
Once decoded, the image can be displayed using tools such as OpenCV. The example code in `2d_data.py` illustrates the explained process.


## `bootup_monitor.py`
The script `bootup_monitor.py` checks that the VPU completes it's boot sequence before attempting to initialize an application.

## `can_activate.py`

The CAN interface can only be activate through the JSON configuration with firmware version 1.4.X or higher.

This examples shows how to activate or deactivate the `can0` interface.

## `configuration.py`

The O3R has multiple parameters that have an influence on the point cloud. Some of them affect the raw measurement and others modify how the data is converted into x,y,z, etc values. These parameters can be changed to better fit your applications and the script `configuration.py` presents how. You can refer to [this page](https://ifm3d.com/latest/Technology/3D/index_3d.html) for a detailed description of each parameter.

The ifm3d API provides functions to read and set the configuration of the device. Note that JSON formatting is used for all the configurations.

## `deserialize_rgb.py`

Some of the data provided by the O3R platform needs to be deserialized to be used. 
For more information on the data structures of each buffer please refer to the [Python API documentation](https://api.ifm3d.com/latest/_autosummary/ifm3dpy.deserialize.html).

The usage of the deserializer is the same for all the deserializable buffers: create the object, and call the deserialize function. Follow the example code, `deserialize_rgb.py` for an example on deserializing the `RGBInfoV1` buffer.

## `deserialize_imu.py` and `imu_data.py`

The IMU data can only be accessed with firmware versions 1.4.X or higher, and ifm3d version 1.5.X or higher.

These two examples show how to retrieve IMU data from the device and how to deserialize it.

## `diagnostic.py`
The script `diagnostic.py` contains helper functions for retrieving diagnostics when requested or asynchronously.

## `fw_update_utils.py`

The script `fw_update_utils.py` demonstrates how to perform a firmware update for your O3R system. Additionally, the script includes several utility functions that provide information, such as determining the current firmware version.

## `getting_data*.py`

The recommended way to receive data is to use the callback function, as shown in the `getting_data_callback.py` script. You can register a callback function that will be executed for every received frame, until the program exits. Alternatively, wait for a frame: you just need to call the `WaitForFrame` function, as shown in the `getting_data.py` script. 

## `multi_head.py`
The `multi_head.py` script demonstrates how to retrieve the list of camera heads connected to the VPU and their types. 

## `timestamps.py`

The script `timestamps.py` demonstrate how to get the timestamps and the effect of `sNTP` on the timestamps.
