cmake_minimum_required(VERSION 3.11)
cmake_policy(SET CMP0048 NEW)

project(o3d_exposure_times CXX)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++17, ON -> -std=gnu++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

add_executable(${PROJECT_NAME} o3d_exposure_times.cpp)
target_link_libraries(o3d_exposure_times ${IFM3D_LIBS})
