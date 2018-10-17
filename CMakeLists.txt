cmake_minimum_required(VERSION 3.5)
project(IFM3D_EXAMPLES)

set(CMAKE_MODULE_PATH
    ${IFM3D_EXAMPLES_SOURCE_DIR}/cmake/modules
    ${CMAKE_MODULE_PATH})

# force an out-of-source build of the code
include(MacroOutOfSourceBuild)
macro_ensure_out_of_source_build(
  "Please build ${PROJECT_NAME} out-of-source")
  
# Conditionally turn on/off parts of the build (global-level)
option(BUILD_MODULE_SIMPLEIMAGE "Build the simpleimage module and example" ON)
option(BUILD_MODULE_EXPOSURE_TIMES "Build ex-exposure-times example" ON)
option(BUILD_MODULE_FAST_APP_SWITCH "Build fast-app-switch example" ON)
option(BUILD_MODULE_FILE_IO "Build opencv based file-io example" ON)
option(BUILD_MODULE_GETMAC "Build getmac example" ON)
option(BUILD_MODULE_MULTI_CAMERA_GRABBER "Build multi-camera-grabber example" ON)
option(BUILD_MODULE_PCICCLIENT_ASYNC_MESSAGES "Build pcicclient-async-messages example" ON)
option(BUILD_MODULE_PCICCLIENT_SET_IO "Build pcicclient-set-io example" ON)
option(BUILD_MODULE_TIMESTAMP "Build timestamp example" ON)

################################################
## Bring in dependent projects
################################################
find_package(ifm3d 0.9.0 CONFIG
  REQUIRED COMPONENTS camera framegrabber image pcicclient
  )

if(FORCE_OPENCV3)
  find_package(OpenCV 3 REQUIRED)
elseif(FORCE_OPENCV2)
  find_package(OpenCV 2.4 REQUIRED)
else()
  find_package(OpenCV REQUIRED)
endif()

################################################
## Build the examples
################################################
if(BUILD_MODULE_SIMPLEIMAGE)
  add_definitions(-DBUILD_MODULE_SIMPLEIMAGE=ON)
  add_subdirectory(simpleimage)
endif() 

if(BUILD_MODULE_EXPOSURE_TIMES)
add_definitions(-DBUILD_MODULE_EXPOSURE_TIMES=ON)
add_subdirectory(exposure_time)
endif()

if(BUILD_MODULE_FAST_APP_SWITCH)
add_definitions(-DBUILD_MODULE_FAST_APP_SWITCH=ON)
add_subdirectory(fast_app_switch)
endif()

if(BUILD_MODULE_FILE_IO)
add_definitions(-DBUILD_MODULE_FILE_IO=ON)
add_subdirectory(file_io)
endif()

if(BUILD_MODULE_GETMAC)
add_definitions(-DBUILD_MODULE_GETMAC=ON)
add_subdirectory(getmac)
endif()

if(BUILD_MODULE_MULTI_CAMERA_GRABBER)
add_definitions(-DBUILD_MODULE_MULTI_CAMERA_GRABBER=ON)
add_subdirectory(multi_camera_grabber)
endif()

if(BUILD_MODULE_PCICCLIENT_ASYNC_MESSAGES)
add_definitions(-DBUILD_MODULE_PCICCLIENT_ASYNC_MESSAGES=ON)
add_subdirectory(pcicclient_async_messages)
endif()

if(BUILD_MODULE_PCICCLIENT_SET_IO)
add_definitions(-DBUILD_MODULE_PCICCLIENT_SET_IO=ON)
add_subdirectory(pcicclient_set_io)
endif()


if(BUILD_MODULE_TIMESTAMP)
add_definitions(-DBUILD_MODULE_TIMESTAMP=ON)
add_subdirectory(timestamp)
endif()



