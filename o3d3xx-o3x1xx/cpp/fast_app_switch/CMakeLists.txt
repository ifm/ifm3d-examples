cmake_minimum_required(VERSION 3.11)
cmake_policy(SET CMP0048 NEW)

include(FetchContent)

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

add_executable(${PROJECT_NAME} o3d_fast_app_switch.cpp)
target_link_libraries(${PROJECT_NAME} ${IFM3D_LIBS} ${OpenCV_LIBS})
FetchContent_Declare(
  fmt
  GIT_REPOSITORY https://github.com/fmtlib/fmt.git
  GIT_TAG 9.1.0)
FetchContent_MakeAvailable(fmt)

target_link_libraries(${PROJECT_NAME} ${IFM3D_LIBS} ${OpenCV_LIBS}
                      fmt::fmt-header-only)
