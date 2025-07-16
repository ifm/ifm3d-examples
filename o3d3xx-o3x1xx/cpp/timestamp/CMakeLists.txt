cmake_minimum_required(VERSION 3.11)
cmake_policy(SET CMP0048 NEW)

project(ex-timestamp CXX)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++17, ON -> -std=gnu++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

include(FetchContent)
FetchContent_Declare(
  fmt
  GIT_REPOSITORY https://github.com/fmtlib/fmt.git
  GIT_TAG 8.0.1)
FetchContent_MakeAvailable(fmt)

add_executable(${PROJECT_NAME} ex-timestamp.cpp)
target_link_libraries(${PROJECT_NAME} ${IFM3D_LIBS} fmt::fmt)
