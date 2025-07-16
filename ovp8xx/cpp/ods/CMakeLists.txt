cmake_minimum_required(VERSION 3.11)

project(ods_examples CXX)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

# Find the ifm3d package
find_package(ifm3d REQUIRED)
# Find the ifm3d package, handling different versions
if(ifm3d_VERSION VERSION_GREATER_EQUAL "1.6.8")
  set(IFM3D_LIBS ifm3d::ifm3d)
elseif(ifm3d_VERSION VERSION_LESS "1.6.8")
  find_package(ifm3d REQUIRED CONFIG COMPONENTS device framegrabber deserialize
                                                swupdater)
  set(IFM3D_LIBS ifm3d::device ifm3d::framegrabber ifm3d::deserialize
                 ifm3d::swupdater)
else()
  message(STATUS "Found ifm3d version ${ifm3d_VERSION} is not compatible.")
endif()

# Find OpenCV
find_package(OpenCV REQUIRED)
# Include directories for OpenCV
include_directories(${OpenCV_INCLUDE_DIRS})

# Copy the config files used by the executables
add_custom_target(
  copyConfigs ALL
  COMMAND
    ${CMAKE_COMMAND} -E copy_directory ${CMAKE_CURRENT_SOURCE_DIR}/configs/
    ${CMAKE_CURRENT_BINARY_DIR}/../configs
  COMMENT "Copying the configs files to the build directory")

# ods_config executables
add_executable(ods_config ods_config.cpp)
target_link_libraries(ods_config PRIVATE ${IFM3D_LIBS})

add_executable(ods_presets ods_config_presets.cpp)
target_link_libraries(ods_presets ${IFM3D_LIBS})

# ods_get_data executable
add_executable(ods_get_data ods_get_data_main.cpp)
target_link_libraries(ods_get_data PRIVATE ${IFM3D_LIBS})
