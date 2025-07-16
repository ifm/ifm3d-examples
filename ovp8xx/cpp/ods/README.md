# ODS examples

The example scripts provided are intended to be used as teaching resources and as building block in more complex applications. The user is free to disassemble, extend, or do whatever they please with this code. All the functions needed to work with an ODS applications are part of the ifm3d library. The rest of the code is added to simplify readability, usage and error handling.

## Overview

The ODS scripts all include a callback to monitor diagnostics with a focus on the application status. As soon as a new diagnostic appears, the status of the application is monitored (`no_incident`, `info`, `minor`, `major`, `critical`). The ODS scripts are briefly described below:

- `ods_config.cpp` demonstrates how to set simple ODS JSON configurations on the O3R platform.
- `ods_config_preset.cpp` demonstrates how to set advanced ODS JSON configurations, including presets, on the O3R platform.
- `ods_get_data.hpp` and `ods_get_data_main.cpp` demonstrates how to receive ODS data from the O3R platform.

> Note: The scripts mentioned above do not take into account all that is necessary for a production application to function long term. We de not handle deployment details, for instance using Docker, or specific error handling strategies, like turning off cameras if overheating or restarting the data stream if it was interrupted.

## Configuration

The examples use sample JSON configuration files that contain dummy camera calibration and application parameters. These files expect specific camera ports (3D cameras on ports 2 and 3). If your setup differs, edit the configuration files in `/configs`. Make sure to recompile the code after changing the configuration files, because they are copied as part of the compilation process.
