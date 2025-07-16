# PDS examples

The example scripts provided are intended to be used as teaching resources and as building blocks for more complex applications. The user is free to disassemble, extend, or modify this code as needed. All the functions required to work with PDS applications are part of the `ifm3d` library. The rest of the code is added to improve readability, usability, and error handling.

## Overview

The PDS scripts all include a callback to monitor diagnostics with a focus on the application status. As soon as a new diagnostic appears, the status of the application is monitored (`no_incident`, `info`, `minor`, `major`, `critical`). The PDS scripts are briefly described below:

- `get_pallet.cpp` demonstrates how to set PDS configurations on the O3R platform, trigger the `getPallet` command, and receive the result.
- `get_pallet_run.cpp` demonstrates how to set PDS configurations on the O3R platform and run the `getPallet` command continuously to receive results.
- `get_pallet_with_tof_image.cpp` demonstrates how to set PDS configurations, trigger the `getPallet` command, and receive both the result and the image.
- `get_rack.cpp` demonstrates how to set PDS configurations, trigger the `getRack` command, and receive the result.
- `vol_check.cpp` demonstrates how to set PDS configurations, trigger the `volCheck` command, and receive the result.
- `get_flags.cpp` demonstrates how to set PDS configurations, trigger the `volCheck` command, and display the result flags.

> **Note**: The scripts above do not cover all requirements for a production-ready application. They do not handle deployment (e.g., using Docker) or advanced error-handling strategies such as disabling cameras when overheating or restarting data streams when interrupted.

## Configuration

The examples use sample JSON configuration files that contain dummy camera calibration and application parameters. These files expect specific camera ports (3D camera on port 2). If your setup differs, edit the configuration files in the `/configs` directory.
