# Python Examples
in this Branch you learn how to work with `ifm3dpy` library. The script examples are divided depending on the use case:
1. **Core:** containing general scripts for O3R system.
2. **ODS:** containing ODS example scripts.
3. **Toobox** containing useful scripts.

## Core
In the Core directory you find multiple general O3R scripts, for instance:
* `2d_data.py`: shows how to receive 2d data.
* `configuration.py`: presents how to configure the O3R parameters
* `deserialize.py`: presents an example on how to deserialize the O3R data.
* `getting_data.py`: presents how to get the data.
* `multi_head.py`: demonstrates how to know the connected heads to the VPU. 
* `ifm3dpy_viewer.py`: presents a full demonstration for viewing different images.
* `fw_update_utils.py`: demonstrates how to perform a firmware update for your O3R system. 
* `timestamps.py`: demonstrate how to get the timestamps and the effect of `sNTP` on the timestamps.
* `diagnostic.py` contains helper functions for retrieving diagnostics when requested or asynchronously.
* `bootup_monitor.py` checks that the VPU completes it's boot sequence.

## ODS
The ODS directory contains Python scripts including:
* `bootup_monitor.py`: Checks that the VPU completes it's boot sequence before attempting to initialize an application.
* `diagnostic.py`: Contains helper functions for retrieving diagnostics when requested or asynchronously.
* `ods_config.py`: demonstrates how to set JSON configurations to the O3R system following the O3R schema. 
* `ods_data_analyze.py`: ods data analyzer script from a h5 file.
* `ods_queue.py` : This script handles the data queues of an ODS application.
* `ods_stream.py` : Provides functions showcasing how to receive data from the O3R platform
* `ods_visualization.py`: is a script used for ODS visualization.
* `ods_demo.py`: is using the described scripts to do a full demonstration of the ODS application.

## Tool box
Within the Toolbox, you find helper scripts, including:
* Angle converter
* Extrinsic calibration:
    * `extrinsic_calib_verification.py`: is a script to verify the extrinsic calibration from h5 data.
* H5 to ifm3d lib converter
* 2D-3D registration script
