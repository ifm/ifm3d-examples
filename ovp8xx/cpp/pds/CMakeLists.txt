cmake_minimum_required(VERSION 3.11)

project(pds_examples CXX)

#Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

#find ifm3d on the system
find_package(ifm3d 1.5.3 CONFIG
  REQUIRED COMPONENTS device framegrabber deserialize
  )

## Volume check example
add_executable(vol_check vol_check.cpp)
target_link_libraries(vol_check
                      ifm3d::device
                      ifm3d::framegrabber
                      )  

## Get pallet example
add_executable(get_pallet get_pallet.cpp)
target_link_libraries(get_pallet
                      ifm3d::device
                      ifm3d::framegrabber
                      )  

## Get item example
# add_executable(get_item get_item.cpp)
# target_link_libraries(get_item
#                       ifm3d::device
#                       ifm3d::framegrabber
#                       )   
## Get rack example
add_executable(get_rack get_rack.cpp)
target_link_libraries(get_rack
                      ifm3d::device
                      ifm3d::framegrabber
                      )                                                         
## Get rack example
add_executable(get_flags get_flags.cpp)
target_link_libraries(get_flags
                    ifm3d::device
                    ifm3d::framegrabber
                    )           