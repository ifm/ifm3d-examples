# Python examples

## Dependencies
Our examples rely on a number of other Python packages listed in the `requirements.txt` file. Before running the examples, install the dependencies with (from the `/python` folder):
```sh
$ pip install -r requirements.txt
```

## Package installation (for ODS examples)
You can skip this step if you are *only* going to use examples in the `core` or `toolbox` folders.

The examples in this repository are available as a Python package that can be locally installed. 
Examples in the ODS folder depend on each other and on core examples. Therefore, to simplify importing and reusing code, you will need to instal the package.

From the `/python` folder, run the following command:
```sh
$ pip install .
```
This will install a packaged called `ovp8xxexamples`.

You can now run the ODS examples.
