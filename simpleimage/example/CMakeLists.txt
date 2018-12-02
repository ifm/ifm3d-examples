
################################################
## Build the examples
################################################

add_executable(ex-simpleImage_ppm_io ex-simpleImage_ppm_io.cpp)

target_link_libraries(ex-simpleImage_ppm_io
                      ifm3d::camera
                      ifm3d::framegrabber
					  simpleimage
					  ppmio
                      )

