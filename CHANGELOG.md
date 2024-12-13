# Changelog for ifm3d-examples

## 1.3.0 (unreleased)
- Add Python and C++ examples for PDS.
- Add Python and C++ examples showing how to use the presets for ODS.

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