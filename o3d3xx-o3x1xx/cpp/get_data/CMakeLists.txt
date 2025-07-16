cmake_minimum_required(VERSION 3.11)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++17, ON -> -std=gnu++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

add_executable(get_data_callback get_data_callback.cpp)
target_link_libraries(get_data_callback ${IFM3D_LIBS})

add_executable(get_data_trigger get_data_trigger.cpp)
target_link_libraries(get_data_trigger ${IFM3D_LIBS})
