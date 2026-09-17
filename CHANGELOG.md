# Changelog for ifm3d-examples

## 1.4.1

- Update the OVP8xx firmware update example with a complete workflow including hardware detection, recovery-mode handling, configuration backup and restore, logging, and boot monitoring. Add a simplified firmware update example for introductory use.
- Add OVP8xx C++ IMU data examples, including a legacy implementation for ifm3d versions before 1.6.15 and an implementation using the IMUInfoV1 deserializer for ifm3d 1.6.15 and newer.
- Add an OVP8xx Python toolbox example to undistort images.
- Update the OVP8xx bootup monitor to poll `/device/status` until the device reaches `OPERATE`, and use it in related CAN activation and reboot flows.
- Improve the O3R password manager example with boot monitoring, password handling cleanup, and firewall configuration checks.
- Add and reorganize O3D3xx and O3X1xx Python examples for data acquisition, buffer rendering, diagnostics, and deserialization. Add sample buffer-rendering assets.
- Add an O3X C++ OpenCV example for visualizing radial distance data, and rename O3D3xx C++ examples to use `o3d_*` file names consistently.
- Update C++ CMake compatibility handling for ifm3d 1.6.x and add fmt where needed. Update Python requirements to newer ifm3dpy versions and related dependencies.
- Correct PLC application scripts and update affected OVP8xx Python examples for the newer APIs.

## 1.4.0

- Update CMakeLists.txt files to handle ifm3d API versions greater than v1.6.8
- Update Python and C++ examples for ODS application showing the diagnostics severity and Polar Occupancy Grid.
- Add Python and C++ examples for password management introduced in 1.21.6 FW for OVP81x VPU.
- Add Python example script for SCC Calibration.

## 1.3.0


- Add Python and C++ examples for PDS.
- Add Python and C++ examples showing how to use the presets for ODS.
- Update the O3R firmware update script to simplify it and remove outdated update processes. Add a C++ version of the script.

## 1.2.1

- Changed the Python example on how to activate the CAN interface on the OVP to check if the CAN interface is available instead of checking for a specific firmware version.
- Add Python and C++ examples on how to deserialize information contained in the `TOF_INFO` buffer.
- Add Python and C++ examples on how to retrieve the JSON schema.
- Add a Dockerfile to change the CAN bitrate and sample-point.
- Reset the validator's schema at every call in the ODS configuration example.
- Update the ifm3d playground to use the `Port` function to get the PCIC port.
- Update the Python `update_settings_to_new_fw_schema.py` example to create a `logs` directory if it does not already exist.
- Add Python and C++ examples for the O3D3xx and O3X1xx devices to get data using a callback or a single frame
- Add Python and C++ examples for the O3D3xx to deserialize several buffers and unpack diagnostic data for the O3D3xx camera.
- Add a folder for examples common to the three device types.
- Add Python and C++ examples on how to identify the format of data in a buffer.
- Fix `ssh_key_gen.py` overwrites authorized keys rather than append to them.

## 1.2.0

- Update the examples for O3D3xx and O3X1xx for ifm3d 1.5.3.
- Deprecate the O3D3xx and O3X1xx image_rectification and intrinsic_to_cartesian examples due to incompatibilities with the updated library. These examples can be updated upon request.

## 1.1.0

- Add a Dockerfile example for CAN usage on the OVP,
- Add a Python example on how to activate the CAN interface on the OVP,
- Add a Python example to get data from the IMU and another to deserialize it,
- Add a Python example to generate SSH keys,
- Add a Python example to update a JSON configuration from one firmware version to another,
- Improve the Python firmware utils example (code cleanup, bootup monitoring, ...),
- Update the versions of the required Python packages.

## 1.0.0

- Initial release: added examples in Python and C++ for the OVP8xx devices,

## 0.1.0

- This is a release for examples for O3D and O3X devices using ifm3d < 1.0.0 (tested with ifm3d v0.11.0)
