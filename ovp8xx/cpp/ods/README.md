# ODS examples

## Overview

The example files provided in this mini-library are intended to be used as teaching resources and as building block in more complex applications. The user is free to disassemble, extend, or do whatever they please with this code. All the functions needed to work with an ODS applications are part of the ifm3d library. The rest of the code is added to simplify readability, usage and error handling.
- `ods_config.h` and `ods_config_main.cpp` show how to get and set configurations on the O3R platform. The header files can be reused in other applications that need configurations functionalities. This example showcases the use of a JSON validator that provides verbose errors when wrong configurations are provided.
- `ods_get_data.h` and `ods_get_data_main.cpp` show how to properly start the data stream, implement a callback that will fill a queue with data, and retrieve data from the queue. Use the header file to make use of the data queue or of the data streamer in your application.

In `ods_demo.cpp`, we show how all these pieces can be used together to form a complete ODS application:
- We configure two applications, one for the “front” view and one for the “back” view,
- We start streaming data from the front view and display it,
- After some seconds, we switch view to use the “back” view, and display the data,
- In parallel, we display the diagnostic messages as they are received from the O3R.

>Note: The scripts mentioned above do not take into account all that is necessary for a production application to function long term. We de not handle deployment details, for instance using docker, or specific error handling strategies, like turning off cameras if overheating or restarting the data stream if it was interrupted.

## Configuration
The examples use example JSON configuration files which contain dummy camera calibration and application parameters. These example files expect specific camera ports (3D cameras in ports 2 and 3). If your setup is different, edit the configuration files in `/ods/configs`. Make sure to recompile the code after changing the configuration files, because they are copied as part of the compilation process.