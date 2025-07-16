cmake_minimum_required(VERSION 3.11)
cmake_policy(SET CMP0048 NEW)

project(ex-fast_app_switch CXX)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++17, ON -> -std=gnu++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

message(STATUS "OpenCV dirs $ENV{OPENCV_DIR}")
message(STATUS "Include dirs OpenCV $ENV{OpenCV_INCLUDE_DIRS}")
message(STATUS "Link Libraries OpenCV $ENV{OpenCV_LIBS}")

find_package(OpenCV REQUIRED)
include_directories(${OpenCV_INCLUDE_DIRS})

add_executable(${PROJECT_NAME} ex-fast_app_switch.cpp)
target_link_libraries(${PROJECT_NAME} ${IFM3D_LIBS} ${OpenCV_LIBS})
