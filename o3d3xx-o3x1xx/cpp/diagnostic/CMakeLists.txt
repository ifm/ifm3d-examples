cmake_minimum_required(VERSION 3.11)

#Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

#find ifm3d on the system
find_package(ifm3d 1.5.3 CONFIG
  REQUIRED COMPONENTS device framegrabber
  )
## Configuration example
add_executable(o3d_diagnostic o3d_diagnostic.cpp)
target_link_libraries(o3d_diagnostic
                      ifm3d::device
                      ifm3d::framegrabber
                      )