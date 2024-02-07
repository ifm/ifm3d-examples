# How to use these examples

## Pre-requisites

- The [ifm3d library >= v1.2.6](https://api.ifm3d.com/stable/content/installation_instructions/install_binary_package_index.html),
- Optional: 
    - The [`json-schema-validator`](https://github.com/pboettch/json-schema-validator) library, which depends on [`nlohmann-json` >= 3.8.x](https://github.com/nlohmann/json). We use this library to validate configurations before attempting to set them. The `json-schema-validator` library provides a more verbose error handling than ifm3d, which allows to identify precisely where the error is in the provided configuration.

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