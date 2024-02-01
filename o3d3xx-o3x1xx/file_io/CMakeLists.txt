cmake_minimum_required(VERSION 3.11)
cmake_policy(SET CMP0048 NEW)

project(ex-file_io CXX)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++17, ON -> -std=gnu++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

message(STATUS "OpenCV dirs $ENV{OPENCV_DIR}")
message(STATUS "Include dirs OpenCV $ENV{OpenCV_INCLUDE_DIRS}")
message(STATUS "Link Libraries OpenCV $ENV{OpenCV_LIBS}")

find_package(OpenCV REQUIRED)
if( TARGET OpenCV)
  message("opencv target found")
endif()

include_directories(${OpenCV_INCLUDE_DIRS})
##############################################################
## finding the ifm3d lib.
##############################################################
find_package(ifm3d 1.4.3 CONFIG
  REQUIRED COMPONENTS ifm3d::common  device framegrabber
  )

add_executable(${PROJECT_NAME} ex-file_io.cpp)
target_link_libraries(${PROJECT_NAME}
                      ifm3d::common
                      ifm3d::device
                      ifm3d::framegrabber
                      ${OpenCV_LIBS}
                      )

