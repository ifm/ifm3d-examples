cmake_minimum_required(VERSION 3.5)
cmake_policy(SET CMP0048 NEW)

project(ex-file_io CXX)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 14)
set(CMAKE_CXX_STANDARD_REQUIRED true)

if(FORCE_OPENCV3)
  find_package(OpenCV 3 REQUIRED)
elseif(FORCE_OPENCV2)
  find_package(OpenCV 2.4 REQUIRED)
else()
  find_package(OpenCV REQUIRED)
endif()

##############################################################
## finding the ifm3d lib. following find_package(ifm3d ...) is
## not required when building project with ifm3d-example repo
## but add so that user can build this project on its own.
##############################################################
find_package(ifm3d 0.11.0 CONFIG
  REQUIRED COMPONENTS camera framegrabber image
  )

add_executable(ex-file_io ex-file_io.cpp)
target_link_libraries(ex-file_io
                      ifm3d::camera
                      ifm3d::framegrabber
                      ifm3d::image
                      ${OpenCV_LIBRARIES}
                      )

