cmake_minimum_required(VERSION 3.11)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++17, ON -> -std=gnu++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

##############################################################
## finding the ifm3d lib.
##############################################################
find_package(ifm3d 1.5.3 CONFIG
  REQUIRED COMPONENTS device framegrabber deserialize
  )

add_executable(o3d_deserialize o3d_deserialize.cpp)
target_link_libraries(o3d_deserialize
                      ifm3d::deserialize
                      ifm3d::device
                      ifm3d::framegrabber
                      )
