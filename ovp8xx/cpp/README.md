# C++ examples

## Pre-requisites

Refer to the compatibility matrix in [the root README](../../README.md#compatibility) for compatible versions of the ifm3d API with the used Firmware.

- Optional:
  - OpenCV is used to display data and convert data formats. Follow the instructions [here for Linux](https://docs.opencv.org/4.x/d7/d9f/tutorial_linux_install.html) and [here for Windows](https://docs.opencv.org/4.x/d3/d52/tutorial_windows_install.html) to install it.

## Build the examples

Follow the instructions below to build the examples. The commands might need to be updated to run on Windows.

```bash
$ cd cpp
$ mkdir build
$ cd build
$ cmake ..
$ cmake --build .
```

This will create executables for all the examples in the sub-folders:

```bash
$ ls
CMakeCache.txt  CMakeFiles  cmake_install.cmake  Configs  core  Makefile  ods
$ ls core/
2d_data         CMakeLists.txt  deserialize  fw_update   getting_data      multi_head
bootup_monitor  configuration   diagnostic   get_schema  ifm3d_playground  o3r_password_manager
$ ls ods
bootup_monitor  cmake_install.cmake  libods_config_lib.a  ods_config  ods_get_data
CMakeFiles      diagnostic           Makefile             ods_demo
```
## summary of the examples

This directory contains example codes to help you start working with the O3R system.

The available example codes are divided into the following subdirectories:

1. The core examples show you how to use the `ifm3d` API to obtain image data (2D, 3D, distance image, etc.), configure camera parameters, update the embedded firmware, and more.

2. The ODS examples, demonstrates how to work with the Obstacle Detection System (ODS). This includes streaming data, analyzing the data, visualizing results, configuring the ODS, and using diagnostic scripts.

3. The PDS examples, demonstrates how to work with the Pick and Drop System (PDS). This includes streaming data, visualizing results, configuring the PDS, and using diagnostic scripts.

4. The SCC example, demonstrates how to calibrate a 3d camera using the Static Camera Calibration (SCC) algorithm.

## Getting started

A recommended order when getting started with the examples would be as follows:

- Start with the core examples, understanding how to collect data (`getting_data*` and `2d_data`) and how to configure the camera (`configuration`),
- Continue with the diagnostic example (`diagnostic`) to understand how to inspect the current state of the device and react to potential errors,
- Look through the deserialization examples (`deserialize*`) to understand how the non-image data is structured (calibration, camera information, etc).

Once you have a good grasp of the core concepts and tools provided by the ifm3d API, you can move to the applications specific examples or continue with the rest of the core examples.

## Configuration

The examples are setup to "try their best" to run with the current configuration of the device. This means that when a port number is needed, the current configuration will be queried and the first available port used. In absence of configuration, the default IP address will be used.

To change the IP address of the device, you can use an environment variable that will be retrieved in the code:

```bash
# Edit with the IP address of your OVP8xx
# On Linux
$ export IFM3D_IP="192.168.0.69"
# On Windows (standard command prompt)
$ set IFM3D_IP=192.168.0.69
# On Windows (PowerShell)
$ $env:IFM3D_IP = "192.168.0.69"
```

To change the port used, you need to open up the code and edit the port number manually. The structure is already there to be able to use a hardcoded port number, and you just need to uncomment it and edit with your setup.
For example, in the `getting_data_callback.cpp` example, you will see the following lines:

```cpp
/////////////////////////////////////////////////////////
// Alternatively, manually pick the port corresponding
// to your 3D camera (uncomment the line below and comment
// the block above)
/////////////////////////////////////////////////////////
// std::string port_nb = "port2";
// if (o3r->Port(port_nb).type != "3D") {
//   std::cerr << "Please provide a 3D port number." << std::endl;
//   return -1;
// }
// uint16_t pcic_port = o3r->Port(port_nb).pcic_port;
// std::cout << "Using 3D port: " << port_nb << std::endl;
```

Uncomment the lines of code and replace the port number variable string `port_nb`.
Don't forget to compile the code again after making these changes.

### PDS Examples

To build the PDS examples, make sure that the `pds` subdirectory is included in the `CMakeLists.txt`.

#### Requirements

There are different configuration files used for testing the PDS functionalities and it is required to configure the files before running the script.

- Extrinsic calibration of the camera port used for PDS testing.
  - Edit `pds/configs/extrinsics.json` file.
- PDS application instance
  - Edit `pds/configs/pds_minimal_config.json` file.
- If any custom pallet configuration is available
  - Edit `pds/configs/custom_pallet.json` file.
- If any custom rack configuration is available
  - Edit `pds/configs/custom_rack.json` file.

### Available PDS Example scripts

| Example                         | Description                                                             | Output                                                                                                   |
| ------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `get_pallet.cpp`                | Sets PDS application in IDLE state and triggers the `getPallet` command | Outputs the pose of detected pallets.                                                                   |
| `get_pallet_run.cpp`            | Sets PDS application in RUN state and triggers the `getPallet` command  | Outputs the pose of detected pallets.                                                                   |
| `get_pallet_with_tof_image.cpp` | Sets PDS application in IDLE state and triggers the `getPallet` command | Outputs the pose of detected pallet and Amplitude image from the port used for PDS Application        |
| `get_rack.cpp`                  | Sets PDS application in IDLE state and triggers the `getRack` command   | Outputs the pose of detected Rack                                                                        |
| `vol_check.cpp`                 | Sets PDS application in IDLE state and triggers the `volCheck` command  | Outputs the number of pixels and nearest pixel in provided volume of interest                            |
| `get_flags.cpp`                 | Sets PDS application in IDLE state and triggers the `volCheck` command  | Outputs the flag array and which flags are set for configured _target_pixel_ in `flag_callback` function |
