
This Docker image provides some of the tensorRT examples provided by NVIDIA. The Dockerfile expresses a multistage build which provides a way of separation of the build and deploy stage. In the deployed image there are no build tools installed to keep the footprint small.

## Testing the TensorRT capabilities

During the build the examples are copied to `/opt/ifm/tensorrt/` instead to the default location `/usr/src/tensorrt` due to the fact that the NVIDIA Docker runtime overloads this folder with the data installed on the VPU, but the OS does not come with the examples pre installed.

```bash
./trtexec --deploy=/opt/ifm/tensorrt/data/mnist/mnist.prototxt --model=/opt/ifm/tensorrt/data/mnist/mnist.caffemodel --output=prob --batch=16 --saveEngine=/tmp/mnist16.trt
./trtexec --loadEngine=/tmp/mnist16.trt --batch=16
```
