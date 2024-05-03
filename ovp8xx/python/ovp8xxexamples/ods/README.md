# ODS

## Overview
The ODS Python scripts will be briefly described below:

- `ods_config.py` demonstrates how to set JSON configurations to the O3R system following the O3R schema. 
- `ods_queue.py` handles the data queues of an ODS application.
- `ods_stream.py` provides functions showcasing how to receive data from the O3R platform
- `ods_visualization.py` is a script used for ODS visualization.
- `ods_demo.py` is using the other scripts to do a full demonstration of the ODS application.
- `transform_cell_to_user.py` showcases how to transform the occupancy grid cell index to coordinates in the user frame.

## Configuration

The examples use example JSON configuration files which contain dummy camera calibration and application parameters. These example files expect specific camera ports (3D cameras in ports 2 and 3). If your setup is different, edit the configuration files in `/ods/configs`.