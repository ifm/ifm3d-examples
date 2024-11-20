# `o3r-l4t-tensorrt`

## Dockerfile content and usage objective
The Dockerfiles provided here serve as a sample code project for using (base) Docker containers on the OVP80x VPU hardware architecture.

Please use the provided `build.sh`, `config.sh` and `run.sh` helper scripts to build and run the images and containers based on the Dockerfiles.
The helper files are not intended to be used as a deployment tool, but rather as a centralized text-based documentation tool of versions and dependencies.

This Docker image provides some of the TensorRT examples provided by NVIDIA. The Dockerfile uses a multistage build which provides a way of separating the build and deploy stages. In the deployed image there are no build tools installed to keep the footprint small.

## Testing the TensorRT capabilities

During the build, the examples are copied to `/opt/ifm/tensorrt/` instead of the default location `/usr/src/tensorrt`, due to the fact that the NVIDIA Docker runtime overloads this folder with the data installed on the VPU, but the OS does not come with the examples preinstalled.

```bash
./trtexec --deploy=/opt/ifm/tensorrt/data/mnist/mnist.prototxt --model=/opt/ifm/tensorrt/data/mnist/mnist.caffemodel --output=prob --batch=16 --saveEngine=/tmp/mnist16.trt
./trtexec --loadEngine=/tmp/mnist16.trt --batch=16
```


## EXCLUSION OF LIABILITY

**DISCLAIMER**:

This software and the accompanying files are provided "as is" and without warranties as to performance, merchantability, or any other warranties whether expressed or implied. The user must assume the entire risk of using the software.

**LIABILITY**:

In no event shall the author or contributors be liable for any special, incidental, indirect, or consequential damages whatsoever (including, without limitation, damages for loss of business profits, business interruption, loss of business information, or any other pecuniary loss) arising out of the use of or inability to use this software, even if the author or contributors have been advised of the possibility of such damages.