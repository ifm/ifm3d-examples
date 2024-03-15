# Python examples

## Dependencies
Our examples rely on a number of other Python packages listed in the `requirements.txt` file. Before running the examples, install the dependencies with (from the `/python` folder):
```sh
$ pip install -r requirements.txt
```

## Package installation (optional)
You can skip this step if you are *only* going to use examples in the `core` or `toolbox` folders.

The examples in this repository are available as a Python package that can be locally installed. 
Examples in the ODS folder depend on each other and on core examples. Therefore, to simplify importing and reusing code, you will need to install the package.

From the `/python` folder, run the following command:
```sh
$ pip install -e .
```
This will install a packaged called `ovp8xxexamples`.

You can now run the ODS examples.

## Configuration
The examples are setup with some default values for variables like the IP address or the camera ports. If the example Python package was installed (see [section above](#package-installation-optional)), default values are defined in the `config.py` file. Otherwise, hardcoded default values are defined in each example, typically with the default IP address 192.168.0.69 and a 2D camera on port 0 and a 3D on port 2. To use a different setup than the default one, you will need to edit the `config.py` file or edit the individual examples with your configuration. 