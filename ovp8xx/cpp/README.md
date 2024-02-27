# C++ examples

## Pre-requisites

- The [ifm3d library >= v1.2.6](https://api.ifm3d.com/stable/content/installation_instructions/install_binary_package_index.html),
- Optional: 
    - The [`json-schema-validator`](https://github.com/pboettch/json-schema-validator) library, which depends on [`nlohmann-json` >= 3.8.x](https://github.com/nlohmann/json). We use this library to validate configurations before attempting to set them. The `json-schema-validator` library provides a more verbose error handling than ifm3d, which allows to identify precisely where the error is in the provided configuration.
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
$ ls core
2d_data     cmake_install.cmake  deserialize   getting_data_callback  Makefile
CMakeFiles  configuration        getting_data  ifm3d_playground       multi_head
$ ls ods
bootup_monitor  cmake_install.cmake  libods_config_lib.a  ods_config  ods_get_data
CMakeFiles      diagnostic           Makefile             ods_demo
```

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