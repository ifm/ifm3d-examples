cmake_minimum_required(VERSION 3.11)

project(ods_examples CXX)

#Global compiler flags
set(CMAKE_BUILD_TYPE Release) # Release or Debug
set(CMAKE_CXX_EXTENSIONS OFF) # OFF -> -std=c++14, ON -> -std=gnu++14
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED true)

#find ifm3d on the system
find_package(ifm3d 1.4.2 CONFIG
REQUIRED COMPONENTS device framegrabber deserialize
)

# Copy the config files used by the executables
add_custom_target(copyConfigs ALL
  COMMAND ${CMAKE_COMMAND} -E copy_directory ${CMAKE_CURRENT_SOURCE_DIR}/Configs/ ${CMAKE_CURRENT_BINARY_DIR}/../Configs
  COMMENT "Copying the configs files to the build directory"
  )

add_executable(ods_config ods_config.cpp)
#Optional json validator package:
find_package(nlohmann_json_schema_validator)
message(Schema found: ${nlohmann_json_schema_validator_FOUND})

add_library(ods_config_lib ods_config.h)
set_target_properties(ods_config_lib PROPERTIES LINKER_LANGUAGE CXX)
if (nlohmann_json_schema_validator_FOUND)
  target_compile_definitions(ods_config_lib PUBLIC "USE_JSONSCHEMA")
  target_link_libraries(ods_config_lib
    nlohmann_json_schema_validator 
  )
endif()

target_link_libraries(ods_config_lib
  ifm3d::device
)  
target_link_libraries(ods_config
  ods_config_lib
  ifm3d::device
)  

add_executable(ods_get_data ods_get_data.cpp)
target_link_libraries(ods_get_data
                      ods_config_lib
                      ifm3d::device
                      ifm3d::framegrabber
                      ifm3d::deserialize
)

add_executable(diagnostic diagnostic.cpp)
target_link_libraries(diagnostic
                      ifm3d::device
                      ifm3d::framegrabber
)            

add_executable(bootup_monitor bootup_monitor.cpp)
target_link_libraries(bootup_monitor
                      ifm3d::device
                      ) 

add_executable(ods_demo ods_demo.cpp)
target_link_libraries(ods_demo
                    ods_config_lib
                    ifm3d::device
                    ifm3d::framegrabber
)                   