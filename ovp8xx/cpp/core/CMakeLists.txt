cmake_minimum_required(VERSION 3.16)

#Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)


SET(IFM3D_VERSION "1.5.3" CACHE STRING "The minimum version of ifm3d to use")
#find ifm3d on the system
find_package(ifm3d ${IFM3D_VERSION} CONFIG
  REQUIRED COMPONENTS device framegrabber deserialize
  )

project(ifm3d_examples CXX)


##############################################################
## Building the examples
##############################################################

## 2d-jpeg-data example with opencv
find_package(OpenCV COMPONENTS core highgui QUIET)
if(OpenCV_FOUND)
add_executable(2d_data 2d_data/2d_data.cpp)
    target_link_libraries(2d_data
                        ${OpenCV_LIBS}
                        ifm3d::device
                        ifm3d::framegrabber
                        )
endif()

## Bootup monitoring example
add_executable(bootup_monitor bootup_monitor/bootup_monitor_main.cpp)
target_link_libraries(bootup_monitor
                      ifm3d::device
                      )                      

## Configuration example
add_executable(configuration configuration/configuration.cpp)
target_link_libraries(configuration
                      ifm3d::device
                      )

                                            
## Deserializer examples
add_executable(deserialize_rgb deserialize/deserialize_rgb.cpp)
target_link_libraries(deserialize_rgb
                      ifm3d::device
                      ifm3d::framegrabber
                      ifm3d::deserialize
                      )
                      
add_executable(deserialize_tof_info deserialize/deserialize_tof_info.cpp)
target_link_libraries(deserialize_tof_info
                      ifm3d::device
                      ifm3d::framegrabber
                      ifm3d::deserialize
                      )

## Diagnostics example
add_executable(diagnostic diagnostic/diagnostic_main.cpp)
target_link_libraries(diagnostic
                      ifm3d::device
                      ifm3d::framegrabber
                      )     

# Get JSON schema example
add_executable(get_schema get_schema/get_schema.cpp)
target_link_libraries(get_schema
                      ifm3d::device
                      )

## Getting data example
add_executable(getting_data getting_data/getting_data.cpp)
target_link_libraries(getting_data
                      ifm3d::device
                      ifm3d::framegrabber
                      )

## Getting data example
add_executable(getting_data_callback getting_data/getting_data_callback.cpp)
target_link_libraries(getting_data_callback
                      ifm3d::device
                      ifm3d::framegrabber
                      )
                                            
## ifm3d-example playground 
add_executable(ifm3d_playground ifm3d_playground/ifm3d_playground.cpp)
target_link_libraries(ifm3d_playground
                      ifm3d::device
                      ifm3d::framegrabber
                      )
## Multi head example
add_executable(multi_head multi_head/multi_head.cpp)
target_link_libraries(multi_head
                      ifm3d::device
                      ifm3d::framegrabber
                      )
