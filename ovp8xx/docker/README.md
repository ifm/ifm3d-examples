# Docker examples

## Available examples

The following example Dockerfiles are provided:

- `o3r-l4t-base` provides a base Dockerfile to build an image based on Ubuntu 18.04 containing the necessary libraries to enable GPU acceleration with CUDA. The `o3r-l4t-base` container is intended to be run on board the OVP8xx.
- `o3r-l4t-tensorrt` builds on top of the base L4T image and includes the TensorRT examples provided by NVIDIA ready to be run. The `o3r-l4t-tensorrt` container is intended to be run on board the OVP8xx.
- Under the `can` directory, there is a Dockerfile with a Python example demonstrating how to deploy a Python script on the VPU using the CAN interface of the VPU. Another Dockerfile can be found in the subfolder `sample-point`, where the example showcases how to change the CAN bitrate and sample point of the CAN interface on the VPU.

## EXCLUSION OF LIABILITY

**DISCLAIMER**:

This software and the accompanying files are provided "as is" and without warranties as to performance, merchantability, or any other warranties whether expressed or implied. The user must assume the entire risk of using the software.

**LIABILITY**:

In no event shall the author or contributors be liable for any special, incidental, indirect, or consequential damages whatsoever (including, without limitation, damages for loss of business profits, business interruption, loss of business information, or any other pecuniary loss) arising out of the use of or inability to use this software, even if the author or contributors have been advised of the possibility of such damages.

## Further documentation

See the respective documentation on the [ifm3d developer portal](https://ifm3d.com/latest/SoftwareInterfaces/Docker/index_docker.html).
