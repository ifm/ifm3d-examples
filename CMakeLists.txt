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
add_definitions(-BUILD_MODULE_EXPOSURE_TIMES=ON)
add_subdirectory(exposure_time)
endif()

if(BUILD_MODULE_FAST_APP_SWITCH)
add_definitions(-BUILD_MODULE_FAST_APP_SWITCH=ON)
add_subdirectory(fast_app_switch)
endif()

if(BUILD_MODULE_FILE_IO)
add_definitions(-BUILD_MODULE_FILE_IO=ON)
add_subdirectory(file_io)
endif()

if(BUILD_MODULE_GETMAC)
add_definitions(-BUILD_MODULE_GETMAC=ON)
add_subdirectory(getmac)
endif()


add_executable(ex-pcicclient_set_io ex-pcicclient_set_io.cpp)
target_link_libraries(ex-pcicclient_set_io
                      ifm3d::camera
                      ifm3d::pcicclient
                      )

add_executable(ex-pcicclient_async_messages ex-pcicclient_async_messages.cpp)
target_link_libraries(ex-pcicclient_async_messages
                      ifm3d::camera
                      ifm3d::pcicclient
                      )

add_executable(ex-timestamp ex-timestamp.cpp)
target_link_libraries(ex-timestamp
                      ifm3d::camera
                      ifm3d::framegrabber
                      ifm3d::image
                      )



add_executable(ex-multi_camera_grabber ex-multi_camera_grabber.cpp)
target_link_libraries(ex-multi_camera_grabber
                    ifm3d::camera
                    ifm3d::framegrabber
                    ifm3d::image
                    )
