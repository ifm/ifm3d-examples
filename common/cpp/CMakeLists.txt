cmake_minimum_required(VERSION 3.11)

project(o3r_examples CXX)

#Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++17, ON -> -std=gnu++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

#find ifm3d on the system
find_package(ifm3d 1.5.3 CONFIG
  REQUIRED COMPONENTS device framegrabber deserialize
  )

## Bootup monitoring example
add_executable(get_data_format get_data_format.cpp)
target_link_libraries(get_data_format
                      ifm3d::device
                      ifm3d::framegrabber
                      )      