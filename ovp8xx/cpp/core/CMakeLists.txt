cmake_minimum_required(VERSION 3.16)

include(FetchContent)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

# find ifm3d on the system
find_package(ifm3d REQUIRED)

# Set global include directories
include_directories(${ifm3d_INCLUDE_DIRS})

# ##############################################################################
# Building the examples
# ##############################################################################

# Find the ifm3d package, handling different versions
find_package(ifm3d REQUIRED)

if(ifm3d_VERSION VERSION_GREATER_EQUAL "1.6.0")
  set(IFM3D_LIBS ifm3d::ifm3d)
  message(STATUS "Found ifm3d version ${ifm3d_VERSION} .")

elseif(ifm3d_VERSION VERSION_LESS_EQUAL "1.5.3")
  find_package(ifm3d REQUIRED CONFIG COMPONENTS device framegrabber deserialize
                                                swupdater)
  set(IFM3D_LIBS ifm3d::device ifm3d::framegrabber ifm3d::deserialize
                 ifm3d::swupdater)
  message(STATUS "Found ifm3d version ${ifm3d_VERSION} .")

else()
  message(STATUS "Found ifm3d version ${ifm3d_VERSION} is not compatible.")
endif()

# 2d-jpeg-data example with opencv
find_package(
  OpenCV
  COMPONENTS core highgui
  QUIET)
if(OpenCV_FOUND)
  add_executable(2d_data 2d_data/2d_data.cpp)
  target_link_libraries(2d_data ${OpenCV_LIBS} ${IFM3D_LIBS})
endif()

# Bootup monitoring example
add_executable(bootup_monitor bootup_monitor/bootup_monitor_main.cpp)
target_link_libraries(bootup_monitor ${IFM3D_LIBS})

# Configuration example
add_executable(configuration configuration/configuration.cpp)
target_link_libraries(configuration ${IFM3D_LIBS})

# Deserializer examples
add_executable(deserialize_rgb deserialize/deserialize_rgb.cpp)
target_link_libraries(deserialize_rgb ${IFM3D_LIBS})

add_executable(deserialize_tof_info deserialize/deserialize_tof_info.cpp)
target_link_libraries(deserialize_tof_info ${IFM3D_LIBS})

# Diagnostics example
add_executable(diagnostic diagnostic/diagnostic_main.cpp)
target_link_libraries(diagnostic ${IFM3D_LIBS})

# Get JSON schema example
add_executable(get_schema get_schema/get_schema.cpp)
target_link_libraries(get_schema ${IFM3D_LIBS})

# Getting data example
add_executable(getting_data getting_data/getting_data.cpp)
target_link_libraries(getting_data ${IFM3D_LIBS})

# Getting data example
add_executable(getting_data_callback getting_data/getting_data_callback.cpp)
target_link_libraries(getting_data_callback ${IFM3D_LIBS})

# IMU data example imu_data.cpp requires ifm3d >= 1.6.15 for the built-in
# IMUInfoV1 deserializer. For older versions, imu_data_legacy.cpp is built
# instead with manual deserialization.
if(ifm3d_VERSION VERSION_GREATER_EQUAL "1.6.15")
  add_executable(imu_data imu_data/imu_data.cpp)
  target_link_libraries(imu_data ${IFM3D_LIBS})
  message(
    STATUS "Building imu_data with IMUInfoV1 deserializer (ifm3d >= 1.6.15).")
else()
  add_executable(imu_data_legacy imu_data/imu_data_legacy.cpp)
  target_link_libraries(imu_data_legacy ${IFM3D_LIBS})
  message(
    STATUS
      "Building imu_data_legacy with manual deserialization (ifm3d < 1.6.15).")
endif()

# ifm3d-example playground
add_executable(ifm3d_playground ifm3d_playground/ifm3d_playground.cpp)
target_link_libraries(ifm3d_playground ${IFM3D_LIBS})

# Multi head example
add_executable(multi_head multi_head/multi_head.cpp)
target_link_libraries(multi_head ${IFM3D_LIBS})

# Multi head example
add_executable(fw_update fw_update/fw_update.cpp)
target_link_libraries(fw_update ${IFM3D_LIBS})

# Password manager example
add_executable(o3r_password_manager
               o3r_password_manager/o3r_password_manager.cpp)
target_link_libraries(o3r_password_manager ${IFM3D_LIBS})

FetchContent_Declare(
  fmt
  GIT_REPOSITORY https://github.com/fmtlib/fmt.git
  GIT_TAG 9.1.0)
FetchContent_MakeAvailable(fmt)

# Logging example

# Declare and fetch spdlog
FetchContent_Declare(
  spdlog
  GIT_REPOSITORY https://github.com/gabime/spdlog.git
  GIT_TAG v1.10.0 # or any stable tag you want
)
FetchContent_MakeAvailable(spdlog)

add_executable(logging logging/logging.cpp)
target_link_libraries(logging ${IFM3D_LIBS} spdlog::spdlog_header_only
                      fmt::fmt-header-only)
