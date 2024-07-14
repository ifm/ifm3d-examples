

## Configuration example
add_executable(ifm3d_playground ifm3d_playground.cpp)
target_link_libraries(ifm3d_playground
                      ifm3d::device
                      ifm3d::framegrabber
                      )