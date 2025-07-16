cmake_minimum_required(VERSION 3.11)

project(ovp8xx_pds_examples CXX)

find_package(Threads REQUIRED)

# ##############################################################################
# Building the examples
# ##############################################################################
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

# Copy the config files used by the executables
add_custom_target(
  copyConfigs_PDS ALL
  COMMAND
    ${CMAKE_COMMAND} -E copy_directory ${CMAKE_CURRENT_SOURCE_DIR}/configs/
    ${CMAKE_CURRENT_BINARY_DIR}/configs
  COMMENT "Copying the config files to the build directory")

# Volume check example
add_executable(vol_check vol_check.cpp)
target_link_libraries(vol_check ${IFM3D_LIBS})

# Get pallet example
add_executable(get_pallet get_pallet.cpp)
target_link_libraries(get_pallet ${IFM3D_LIBS})

# Get pallet run example
add_executable(get_pallet_run get_pallet_run.cpp)
target_link_libraries(get_pallet_run ${IFM3D_LIBS} Threads::Threads)

# Get item example add_executable(get_item get_item.cpp)
# target_link_libraries(get_item ${IFM3D_LIBS})

# Get rack example
add_executable(get_rack get_rack.cpp)
target_link_libraries(get_rack ${IFM3D_LIBS})

# Get flags example
add_executable(get_flags get_flags.cpp)
target_link_libraries(get_flags ${IFM3D_LIBS})

# Get pallet+tof example
add_executable(get_pallet_with_tof get_pallet_with_tof_image.cpp)
target_link_libraries(get_pallet_with_tof ${IFM3D_LIBS})
