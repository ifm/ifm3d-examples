
"""
This module provides functions to convert Euler angles between O3R2XX format and human-readable format.

The module performs the following tasks:
- Retrieves the current calibration for a specific camera port of an O3R device.
- Converts the O3R2XX Euler angles to human-readable angles.
- Converts human-readable angles to O3R2XX Euler angles.
- Sets the new calibration for the camera port.

To use this module, you need to edit the IP address and camera port for your device.

Example usage:
    # Convert O3R2XX Euler angles to human-readable angles
    human_read_angles = o3rCalibAnglesToHumanReadable(*euler_rot)

    # Convert human-readable angles to O3R2XX Euler angles
    euler_rot = humanReadableToO3RCalibAngles(roll=ROLL, pitch=PITCH, yaw=YAW)

    # Set the new calibration for the camera port
    o3r.set({
        "ports": {
            CAMERA_PORT: {
                "processing": {
                    "extrinsicHeadToUser": {
                        "rotX": euler_rot[0],
                        "rotY": euler_rot[1],
                        "rotZ": euler_rot[2],
                    }
                }
            }
        }
    })
"""
