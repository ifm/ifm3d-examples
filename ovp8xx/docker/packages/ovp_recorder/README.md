# O3R Black Box Recorder
This black box recorder can be used to record ifm O3R data streams. These include:
+ 3D TOF: normal and debug
+ 2D RGB: normal and debug
+ ODS application streams: normal and debug

The generated files can read back to Python using the provided reader scripts and can be replayed using the ifm Vision Assistant GUI.

## Tested CPU architectures
The tool was tested under:
+ AMD64 architecture
+ ARM64v8 architecture

For running the software locally on a AMD64 based PC, install the Python package and its dependencies in a local Python 3 interpreter.
For running the software on a IPC (arm64v8) hardware please used the provided Dockerfile to create Docker containers that can be deployed, for example on a O3R OVP8xx VPU.

## Docker container
### Building the container

Use the script [`build.sh`](build.sh) to build the Docker container and deploy the image to the connected VPU at its default IP address (`192.168.0.69`)

## Recording

### Recording via Docker container on the VPU

**Build the Docker container**

Use the supplied Dockerfile and helper script for building the container: The container needs to be build to the correct architecture: ARM64V8
Please use qemu for ARM64V8 emulation on a AMD64 based laptop.


**Transfer the container to the VPU**

Option 1: transfer as a tar and unpack on the VPU
Option 2: transfer the container directly from your local Docker instance

For more details see: https://ifm3d.com/documentation/SoftwareInterfaces/Docker/deployVPU.html

Transfer the container to the VPU:
```bash
docker save o3r_data_recorder:v0.1.0 | ssh -C oem@192.168.0.69 docker load
```

**Run the container**

Login into the VPU at its default IP address using the oem user:
```bash
$ ssh oem@192.168.0.69
```

Start the container with a volume: to allow data saving directly to the external USB SSD
```bash
# Check the availability of the external SSD:
$ o3r-vpu-c0:~$ lsusb
Bus 002 Device 002: ID 04e8:4001 Samsung Electronics Co., Ltd PSSD T7
Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub

# The external SSD will be mounted to /run/media/system/<device>
# In this case it is mounted to: /run/media/system/PSSD_T7

# Run the Docker container on the VPU with a volume mounted: make sure you share the host network with the container to allow the socket communication
$ docker run -ti -v /run/media/system/PSSD_T7:/home/ifm/data --network host o3r_data_recorder:v0.1.0
```

> Note: The camera heads data streams may need to be start manually: Please see the respective instructions [here](https://api.ifm3d.com/stable/content/cmdline_configuring.html#setting-multiple-parameters).


**Start a recording**

```bash
$ python3 data_stream_recorder/data_recorder_poc.py port0 port1 port2 port3
```

These parameters have to be set manually to record a certain number of 2D and 3D image streams to an external SSD:
+ `sources`: see command above - `port0 port1 port2 port3` are used to record the data streams at physical ports [0,1,2,3]

The file will be automatically saved to the external SSD as specified in the [`default_values.py` file](data_stream_recorder/configs/default_values.py).


The available commands for argument parsing are:
```bash
root@ovp8xx-3a-45-d0:/app# python3 data_stream_recorder/data_recorder_poc.py --help
usage: data_recorder_poc.py [-h] [--ip IP] [--loglevel {DEBUG,INFO,WARNING,ERROR}] [--timeout TIMEOUT] [--numSeconds NUMSECONDS] [--filename FILENAME] [--forceDisableMotionCompensation] [--useIfm3d] [sources [sources ...]]

positional arguments:
  sources               Sources can be either port[0-6], app[0-9], port[0-6]_AD, and app[0-9]_AD

optional arguments:
  -h, --help            show this help message and exit
  --ip IP               ip address of VPU
  --loglevel {DEBUG,INFO,WARNING,ERROR}
  --timeout TIMEOUT     timeout to be used in the get function
  --numSeconds NUMSECONDS
                        number of seconds to be recorded (default: record until CTRL-C)
  --filename FILENAME   target filename. If not given, a file will be created in the current directory.
  --forceDisableMotionCompensation
                        Force disabling motion compensation during recording.
  --useIfm3d            Use ifm3d library to receive data instead of the pure python implementation. Requires an installed version of ifm3dpy.
```

**Replay a O3R recording**

Recordings recorded with the tool mentioned above are compatible with the ifmVisionAssistant (iVA) version > 2.6.14.