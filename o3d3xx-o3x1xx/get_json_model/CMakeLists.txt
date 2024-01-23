cmake_minimum_required(VERSION 3.11)
cmake_policy(SET CMP0048 NEW)

project(ex-get_json_model CXX)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++17, ON -> -std=gnu++17
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)


##############################################################
## finding the ifm3d lib.
##############################################################
find_package(ifm3d 1.4.3 CONFIG
  REQUIRED COMPONENTS ifm3d::common  device framegrabber
  )

add_executable(${PROJECT_NAME} ex-get_json_model.cpp)
target_link_libraries(${PROJECT_NAME}
                      ifm3d::common
                      ifm3d::device
                      ifm3d::framegrabber
                      )

