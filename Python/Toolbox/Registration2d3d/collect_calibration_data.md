# Collect camera calibration data

Calibration data can be used for odometry or tasks like 2D-3D registration.

<!-- TODOOOO increment this example so that it uses the calibration deserializer -->

## Procedure

1. Clone the documentation repository.
   ```sh
   $ git clone https://github.com/ifm/documentation.git
   ```
2. Create a virtual environment and install the required packages.
    ```sh
   $ python -m venv venv                # create a virtual environment
   $ source venv/bin/activate           # activate the virtual environment
   $ cd .Software_Interfaces/Toolbox/
   $ pip install -r ./Registration2d3d/requirements.txt  # install the required python packages
   ```

3. Run the file example script specifying the IP address of the VPU

    ```
    python ./registration2d3d/collect_calibrations.py --IP 192.168.0.69
    ```

## Example output:


```
Collected calibration data for port 0.
Collected calibration data for port 2.

Port 0 calibrations:
{'ext_optic_to_user': (0.029000205919146538,
                       0.0,
                       0.0173801239579916,
                       -0.0009388890466652811,
                       0.00783364288508892,
                       0.004958024714142084),
 'intrinsic_calibration': (2,
                           578.111328125,
                           578.111328125,
                           632.248046875,
                           403.7044372558594,
                           0.0,
                           -0.0011449999874457717,
                           0.0012159999459981918,
                           -0.000514000013936311,
                           0.0),
 'inverse_intrinsic_calibration': (3,
                                   578.111328125,
                                   578.111328125,
                                   632.248046875,
                                   403.7044372558594,
                                   0.0,
                                   0.000999000039882958,
                                   -0.001028000027872622,
                                   0.0004490000137593597,
                                   0.0)}

Port 2 calibrations:
{'ext_optic_to_user': (0.015000106766819954,
                       0.0,
                       0.008410060778260231,
                       -0.001985065871849656,
                       0.009047729894518852,
                       0.004811344668269157),
 'intrinsic_calibration': (0,
                           131.01919555664062,
                           131.01919555664062,
                           114.1493911743164,
                           83.62940979003906,
                           0.0,
                           0.5029289722442627,
                           -0.40336400270462036,
                           0.0,
                           0.0),
 'inverse_intrinsic_calibration': (1,
                                   131.01919555664062,
                                   131.01919555664062,
                                   114.1493911743164,
                                   83.62940979003906,
                                   0.0,
                                   -0.2719089984893799,
                                   0.05658800154924393,
                                   0.0,
                                   0.0)}
```