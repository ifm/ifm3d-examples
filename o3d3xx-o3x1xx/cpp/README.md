
# ifm3d C++ examples

Beyond providing concrete code examples for interfacing to `ifm3d`, this project also
shows how to integrate `ifm3d` into an external project via `cmake`. This
project relies upon `ifm3d` version 1.4.3 or better. 

This directory contains example programs that utilize `ifm3d`. The
intention is to create standalone programs that illustrate one very specific
concept in order to serve the purpose of letting developers ramp up quickly
with using the library. The build infrastructure in this directory is minimal
and the programs are intended to be run in place. Additionally, unless
specifically stated otherwise, things like performance and robust error
handling are not demonstrated. The purpose is to clearly illustrate the task
without clouding it with the details of real-world software engineering --
unless, of course, that was the point of the example.

It is expected that this library of examples will grow over time in response to
common themes we see on the issue tracker.

##  Prerequisites 
 - [fmt](https://github.com/fmtlib/fmt.git)
 - [openCV](https://opencv.org/releases/)


## Building the examples

Assuming you are starting from the `cpp` directory of this source
distribution:

    $ mkdir build
    $ cd build
    $ cmake ..
    $ cmake --build .

### Windows examples
For Windows-based target, with Visual Studio 2017, assuming you are starting from the top-level directory of this source
distribution:

    $ set IFM3D_CMAKE_GENERATOR="Visual Studio 17 2022"
    $ cd ifm3d-examples/o3d3xx-o3x1xx
    $ mkdir build
    $ cd build
    # Note: To show images Opencv is used,hence build path to opencv is added into -DCMAKE_PREFIX_PATH
    $ cmake -G %IFM3D_CMAKE_GENERATOR% -DCMAKE_WINDOWS_EXPORT_ALL_SYMBOLS=ON -DCMAKE_PREFIX_PATH=F:\windows\ifm3d_deps\install;F:\opencv-4.9.0-windows\opencv\build  ..
    $ cmake --build . --config Release --target ALL_BUILD

At this stage, projects are built and you will find *IFM3D_EXAMPLES.sln* in build folder.
Use Release / RelWithDebInfo configuration to run and investigate application examples.
Please add PATH variable to projects :

    PATH=%IFM3D_BUILD_DIR%\install\bin;%IFM3D_BUILD_DIR%\install\x64\vc%MSVC_MAJOR_VERSION%.%MSVC_MINOR_VERSION%\bin;%PATH%

For instance, you can fill directly in VS *Project Properties* / *Debugging* / *Environment* with                   `PATH=C:\ifm3d\install\bin;C:\ifm3d\install\x64\vc14.1\bin;%PATH%`

## What is included?

- [deserialize](./deserialize/o3d_deserialize.cpp) shows how to extract data from a selected number of buffers, for the O3D camera.
- [diagnostic](./diagnostic/o3d_diagnostic.cpp) shows how ro receive and unpack diagnostic data, for the O3D camera.
- [exposure_time](exposure_time/ex-exposure_times.cpp) shows how to change imager exposure times on the fly while streaming in pixel data and validating the setting of the exposure times registered to the frame data.
- [fast_app_switch](fast_app_switch/ex-fast_app_switch.cpp) shows how to switch between two applications on the camera using PCIC.
- [file_io](file_io/ex-file_io.cpp) shows how to capture data from the camera and write the images to disk. In this example, the amplitude image is written out as PNG files.
- [get_data_callback](./get_data/get_data_callback.cpp) and [get_data_trigger](./get_data/get_data_tigger.cpp) show how to receive data from the device, either continuously using a callback or a single frame using he software trigger.
- [get_json_model](./get_json_model/ex-get_json_model.cpp) shows how to retrieve the JSON model for the device configuration.
- [getmac](getmac/ex-getmac.cpp) request the MAC address from the camera. The MAC address can be used as a unique identifier.
- [multi_camera_grabber](multi_camera_grabber/ex-multi_camera_grabber.cpp) demonstrates how to acquire frames from multiple ifm 3D camera's, see the example [documentation](./multi_camera_grabber/doc/ex-multi_camera_grabber.md) for more details.
- [pcicclient_async_messages](pcicclient_async_messages/ex-pcicclient_async_messages.cpp) shows how to use the PCICClient module to receive asynchronous notification (and error) messages from the camera.
- [pcicclient_set_io](pcicclient_set_io/ex-pcicclient_set_io.cpp) shows how to mutate the digital IO pins on the O3D camera by the PCIC interface.
- [simpleImage_ppm_io](simpleimage/example/ex-simpleImage_ppm_io.cpp) shows how to write your own image container which does not depend on PCL nor OpenCV.
- [timestamp](timestamp/ex-timestamp.cpp) requests some frames from the camera and write the timestamps to stdout.

### Note: Use of `Device` and `LegacyDevice` class

Please note `Device` is the base class and `LegacyDevice` inherits from the `Device` class. Object from `ifm3d::Device` can be created while accessing the device functionalities and `ifm3d::LegacyDevice` object can be created while using the application specific methods of legacy devices like `O3D/O3X`.

## LICENSE
Please see the file called [LICENSE](LICENSE).
