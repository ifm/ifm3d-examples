project(PPMIO CXX)
set(PPMIO_MODULE_NAME "PPMIO")

################################################
## "build" for header-only library
################################################

add_library(ppmio INTERFACE)
target_include_directories(ppmio INTERFACE include/)

target_compile_options(ppmio
  INTERFACE $<$<COMPILE_LANGUAGE:CXX>:-std=c++${CMAKE_CXX_STANDARD}>
  )
set_target_properties(ppmio PROPERTIES
  EXPORT_NAME ppmio
  )
 


