cmake_minimum_required(VERSION 3.11)
project(IFM3D_EXAMPLES)

include(FetchContent)

set(CMAKE_MODULE_PATH ${IFM3D_EXAMPLES_SOURCE_DIR}/cmake/modules
                      ${CMAKE_MODULE_PATH})

# Conditionally turn on/off parts of the build (global-level)
option(BUILD_MODULE_SIMPLEIMAGE "Build the simpleimage module and example" ON)
option(BUILD_EXAMPLE_EXPOSURE_TIMES "Build ex-exposure-times example" ON)
option(BUILD_EXAMPLE_FAST_APP_SWITCH "Build fast-app-switch example" ON)
option(BUILD_EXAMPLE_FILE_IO "Build opencv based file-io example" ON)
option(BUILD_EXAMPLE_GETMAC "Build getmac example" ON)
option(BUILD_EXAMPLE_MULTI_CAMERA_GRABBER "Build multi-camera-grabber example"
       ON)
option(BUILD_EXAMPLE_PCICCLIENT_ASYNC_MESSAGES
       "Build pcicclient-async-messages example" ON)
option(BUILD_EXAMPLE_PCICCLIENT_SET_IO "Build pcicclient-set-io example" ON)
option(BUILD_EXAMPLE_TIMESTAMP "Build timestamp example" ON)
option(BUILD_EXAMPLE_GET_JSON_MODEL "Build get_json_model example" ON)
option(BUILD_EXAMPLE_DIAGNOSTIC "Build o3d_diagnostic example" ON)
option(BUILD_EXAMPLE_GET_DATA "Build the get_data examples" ON)
option(BUILD_EXAMPLE_DESERIALIZE "Build the deserializer example" ON)

# ##############################################################################
# Bring in dependent projects
# ##############################################################################
find_package(ifm3d REQUIRED)

FetchContent_Declare(
  fmt
  GIT_REPOSITORY https://github.com/fmtlib/fmt.git
  GIT_TAG 9.1.0)
FetchContent_MakeAvailable(fmt)

# Find the ifm3d package, handling different versions
if(ifm3d_VERSION VERSION_GREATER_EQUAL "1.6.0")
  set(IFM3D_LIBS ifm3d::ifm3d fmt::fmt-header-only)
elseif(ifm3d_VERSION VERSION_LESS_EQUAL "1.5.3")
  find_package(ifm3d REQUIRED CONFIG COMPONENTS device framegrabber deserialize
                                                swupdater)
  set(IFM3D_LIBS ifm3d::device ifm3d::framegrabber ifm3d::deserialize
                 ifm3d::swupdater fmt::fmt-header-only)
else()
  message(STATUS "Found ifm3d version ${ifm3d_VERSION} is not compatible.")
endif()
# ##############################################################################
# Build the Modules
# ##############################################################################
if(BUILD_MODULE_SIMPLEIMAGE)
  add_definitions(-DBUILD_MODULE_SIMPLEIMAGE=ON)
  add_subdirectory(simpleimage)
endif()

# ##############################################################################
# Build the examples
# ##############################################################################

if(BUILD_EXAMPLE_GETMAC)
  add_definitions(-DBUILD_EXAMPLE_GETMAC=ON)
  add_subdirectory(getmac)
endif()

if(BUILD_EXAMPLE_GET_JSON_MODEL)
  add_definitions(-DBUILD_EXAMPLE_GET_JSON_MODEL=ON)
  add_subdirectory(get_json_model)
endif()

if(BUILD_EXAMPLE_FAST_APP_SWITCH)
  add_subdirectory(fast_app_switch)
endif()

if(BUILD_EXAMPLE_EXPOSURE_TIMES)
  add_subdirectory(exposure_time)
endif()

if(BUILD_EXAMPLE_FILE_IO)
  add_subdirectory(file_io)
endif()

if(BUILD_EXAMPLE_MULTI_CAMERA_GRABBER)
  add_subdirectory(multi_camera_grabber)
endif()

if(BUILD_EXAMPLE_TIMESTAMP)
  add_subdirectory(timestamp)
endif()

if(BUILD_EXAMPLE_PCICCLIENT_ASYNC_MESSAGES)
  add_subdirectory(pcicclient_async_messages)
endif()

if(BUILD_EXAMPLE_PCICCLIENT_SET_IO)
  add_subdirectory(pcicclient_set_io)
endif()

if(BUILD_EXAMPLE_DIAGNOSTIC)
  add_subdirectory(diagnostic)
endif()

if(BUILD_EXAMPLE_GET_DATA)
  add_subdirectory(get_data)
endif()

if(BUILD_EXAMPLE_DESERIALIZE)
  add_subdirectory(deserialize)
endif()
