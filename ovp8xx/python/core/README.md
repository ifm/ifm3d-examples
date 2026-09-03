# Core

In this directory you find multiple general O3R scripts that are explained below.

## `2d_data.py`

Receiving RGB data with `ifm3dpy` is done similarly as 3D data: the core objects have to be instantiated, and a frame has to be retrieved.
The important part is how to access the RGB image and how to decode it for further use.
Once decoded, the image can be displayed using tools such as OpenCV. The example code in `2d_data.py` illustrates the explained process.

## `bootup_monitor.py`

The script `bootup_monitor.py` checks that the VPU completes its boot sequence before attempting to initialize an application. Readiness is detected by polling `/device/status` until it reaches `OPERATE`.

## `can_activate.py`

The CAN interface can only be activate through the JSON configuration with firmware version 1.4.X or higher.
This examples shows how to activate or deactivate the `can0` interface.

## `configuration.py`

The O3R has multiple parameters that have an influence on the point cloud. Some of them affect the raw measurement and others modify how the data is converted into x,y,z, etc values. These parameters can be changed to better fit your applications and the script `configuration.py` presents how. You can refer to [this page](https://ifm3d.com/latest/Technology/3D/index_3d.html) for a detailed description of each parameter.

The ifm3d API provides functions to read and set the configuration of the device. Note that JSON formatting is used for all the configurations.

## `deserialize_*.py`

Some of the data provided by the O3R platform needs to be deserialize to be used.
For more information on the data structures of each buffer please refer to the [Python API documentation](https://api.ifm3d.com/latest/_autosummary/ifm3dpy.deserialize.html).

The usage of the deserializer is the same for all the deserializable buffers: create the object, and call the deserialize function. Follow the example code, `deserialize_rgb.py` for an example on deserializing the `RGBInfoV1` buffer.

## `deserialize_imu.py` and `imu_data.py`

The IMU data can only be accessed with firmware versions 1.4.30 or higher, and ifm3d version 1.5.3 or higher.

These two examples show how to retrieve IMU data from the device and how to deserialize it.

## `diagnostic.py`

The script `diagnostic.py` contains helper functions for retrieving diagnostics when requested or asynchronously.

## `fw_update.py`

This script delivers a complete firmware update workflow for OVP8xx devices: configuration values appear at the top of the file, the O3R object is created once, and the main logic is contained in clearly named helper methods. Key capabilities include automatic hardware detection (OVP80x and OVP81x), coverage of legacy upgrade paths such as 0.16.x ↔ 1.x.x transitions, detailed logging, configuration backup and restore, recovery-mode handling, and boot monitoring. Although it covers a wide range of edge cases, users should validate the procedure by testing on non-production systems first before rolling into production. Firmware update is a critical operation, and care should be taken to ensure that the process completes successfully. Do not interrupt the update once it has started.

Usage example:

```bash
python fw_update.py --firmware-file /path/to/firmware.swu --ip 192.168.0.69
```

## `fw_update_simple.py`

This condensed firmware update example mirrors the basic structure of the other introductory scripts and is intended for educational purposes only. It omits hardware detection, advanced error handling, configuration backup, and other safeguards. Use it to understand the essential API calls, then rely on `fw_update.py` when you need broader coverage of real-world scenarios. Test the complete script in your environment before deploying it on production systems.

## `getting_data*.py`

The recommended way to receive data is to use the callback function, as shown in the `getting_data_callback.py` script. You can register a callback function that will be executed for every received frame, until the program exits. Alternatively, wait for a frame: you just need to call the `WaitForFrame` function, as shown in the `getting_data.py` script.

## `multi_head.py`

The `multi_head.py` script demonstrates how to retrieve the list of camera heads connected to the VPU and their types.

## `timestamps.py`

The script `timestamps.py` demonstrate how to get the timestamps and the effect of `sNTP` on the timestamps.

## `ssh_key_gen.py`

The `ssh_key_gen.py` script demonstrate how to create an SSH key to access to the VPU.
