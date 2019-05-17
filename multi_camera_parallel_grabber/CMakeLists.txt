cmake_minimum_required(VERSION 3.5)

project(ex-multi_camera_parallel_grabber CXX)

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
## finding the ifm3d lib.
##############################################################
find_package(ifm3d 0.11.0 CONFIG
  REQUIRED COMPONENTS camera framegrabber image
  )

find_package(Threads)

add_executable(ex-multi_camera_parallel_grabber ex-multi_camera_parallel_grabber.cpp)
target_link_libraries(ex-multi_camera_parallel_grabber
                      ifm3d::camera
                      ifm3d::framegrabber
                      ifm3d::image
                      ${CMAKE_THREAD_LIBS_INIT}
                      ${OpenCV_LIBRARIES}
                      )
