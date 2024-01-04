# ifm3dpy Viewer

This is an example application for retrieving different kinds of image data from an O3R platform.

### Install requirements
```sh
/path/to/python/executable/python.exe -m pip install -r examples/python/requirements.txt
```

## Usage
```sh
usage: ifm3dpy_viewer.py [-h] --pcic-port PORT --image {jpeg,distance,amplitude,xyz} [--ip IP] [--xmlrpc-port XMLRPC_PORT]

optional arguments:
  -h, --help            show this help message and exit
  --pcic-port PORT      The pcic port from which images should be received
  --image {jpeg,distance,amplitude,xyz}
                        The image to received (default: distance)
  --ip IP               IP address of the sensor (default: 192.168.0.69)
  --xmlrpc-port XMLRPC_PORT
                        XMLRPC port of the sensor (default: 80)
```

### Display the distance image
```sh
python examples/python/viewer/ifm3dpy_viewer.py --pcic-port 50012 --image distance
```

### Display the amplitude image
```sh
python examples/python/viewer/ifm3dpy_viewer.py --pcic-port 50012 --image amplitude
```

### Display the point cloud (requeires open3d)
```sh
python examples/python/viewer/ifm3dpy_viewer.py --pcic-port 50012 --image xyz
```

### Display the jpeg image
```
python examples/python/viewer/ifm3dpy_viewer.py --pcic-port 50010 --image jpeg
```
