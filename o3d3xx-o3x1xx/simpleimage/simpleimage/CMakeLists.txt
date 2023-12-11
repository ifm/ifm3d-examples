
project(SIMPLEIMAGE CXX)
set(SIMPLEIMAGE_MODULE_NAME "simpleimage")

################################################
## "build" for header-only library
################################################
add_library(simpleimage INTERFACE)
target_include_directories(simpleimage INTERFACE include/)

target_compile_options(simpleimage
  INTERFACE $<$<COMPILE_LANGUAGE:CXX>:-std=c++${CMAKE_CXX_STANDARD}>
  )

target_link_libraries(simpleimage
  INTERFACE
    ifm3d::framegrabber
	ifm3d::camera
    )
	
set_target_properties(simpleimage PROPERTIES
  EXPORT_NAME simpleimage
  )



