# Python examples

This directory contains example codes in Python3 to help you start working with the O3R system.

The available example codes are divided into the following subdirectories:

1. The core examples show you how to use the `ifm3d` API to obtain image data (2D, 3D, distance image, etc.), configure camera parameters, update the embedded firmware, and more.

2. The ODS examples, demonstrates how to work with the Obstacle Detection System (ODS). This includes streaming data, analyzing the data, visualizing results, configuring the ODS, and using diagnostic scripts.

3. The PDS examples, demonstrates how to work with the Pick and Drop System (PDS). This includes streaming data, visualizing results, configuring the PDS, and using diagnostic scripts.

4. The SCC example, demonstrates how to calibrate a 3d camera using the Static Camera Calibration (SCC) algorithm.

5. The PLC examples, demonstrates how to send and receive data from the PLC application. These scripts can be used as a base to understand the data structure of the commands that can be sent from PLC to the PLC application and unpack the data from the PLC application.

6. Within the Toolbox, you find various helper scripts that showcase how to use the data for specific applications.

## Dependencies

Our examples rely on a number of other Python packages listed in the `requirements.txt` file. Before running the examples, install the dependencies with (from the `/python` folder):

```sh
$ pip install -r requirements.txt
```
