# Changelog for ifm3d-examples
## Unreleased
- Changed the Python example on how to activate the CAN interface on the OVP to check if the CAN interface is available instead of checking for a specific firmware version.
- Add Python and C++ examples on how to deserialize information contained in the `TOF_INFO` buffer.

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