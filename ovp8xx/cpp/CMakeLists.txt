cmake_minimum_required(VERSION 3.11)

project(o3r_examples CXX)

#Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

#find ifm3d on the system
find_package(ifm3d 1.2.6 CONFIG
  REQUIRED COMPONENTS device framegrabber deserialize
  )

add_subdirectory(ods)
add_subdirectory(core)
