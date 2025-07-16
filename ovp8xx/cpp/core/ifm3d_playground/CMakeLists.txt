cmake_minimum_required(VERSION 3.11)

project(ifm3d_playground CXX)

# Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

# ##############################################################################
# Building the examples
# ##############################################################################
# Find the ifm3d package
find_package(ifm3d REQUIRED)

# Find the ifm3d package, handling different versions
if(ifm3d_VERSION VERSION_GREATER_EQUAL "1.6.8")
  set(IFM3D_LIBS ifm3d::ifm3d)
elseif(ifm3d_VERSION VERSION_LESS "1.6.8")
  find_package(ifm3d REQUIRED CONFIG COMPONENTS device framegrabber deserialize
                                                swupdater)
  set(IFM3D_LIBS ifm3d::device ifm3d::framegrabber ifm3d::deserialize
                 ifm3d::swupdater)
else()
  message(STATUS "Found ifm3d version ${ifm3d_VERSION} is not compatible.")
endif()

# ifm3d playground example
add_executable(ifm3d_playground ifm3d_playground.cpp)
target_link_libraries(ifm3d_playground ${IFM3D_LIBS})
