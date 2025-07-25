# ifm3d examples for OVP8xx

This directory contains example codes in Python3 and C++ to help you start working with the O3R system.

The available example codes are divided into the following subdirectories:

1. The core examples show you how to use the `ifm3d` API to obtain image data (2D, 3D, distance image, etc.), configure camera parameters, update the embedded firmware, and more.

2. The ODS examples, demonstrates how to work with the Obstacle Detection System (ODS). This includes streaming data, analyzing the data, visualizing results, configuring the ODS, and using diagnostic scripts.

3. The PDS examples, demonstrates how to work with the Pick and Drop System (PDS). This includes streaming data, visualizing results, configuring the PDS, and using diagnostic scripts.

4. The SCC example, demonstrates how to calibrate a 3d camera using the Static Camera Calibration (SCC) algorithm.

5. The PLC examples, demonstrates how to send and receive data from the PLC application. These scripts can be used as a base to understand the data structure of the commands that can be sent from PLC to the PLC application and unpack the data from the PLC application (only Python examples available at the moment).

6. Within the Toolbox, you find various helper scripts that showcase how to use the data for specific applications (only Python examples available at the moment).

## Getting started

Each example folder contains a README.md which provides an overview of the available examples and some more detailed explanation of the concepts showed if necessary. We recommend reading through the examples READMEs and the examples code and comments to fully comprehend the concepts.

A recommended order when getting started with the examples would be as follows:

- Start with the core examples, understanding how to collect data (`getting_data*` and `2d_data`) and how to configure the camera (`configuration`),
- Continue with the diagnostic example (`diagnostic`) to understand how to inspect the current state of the device and react to potential errors,
- Look through the deserialization examples (`deserialize*`) to understand how the non-image data is structured (calibration, camera information, etc).

Once you have a good grasp of the core concepts and tools provided by the ifm3d API, you can move to the applications specific examples or continue with the rest of the core examples.
