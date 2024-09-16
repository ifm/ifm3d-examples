# ifm3d examples

This project provides a collection of code examples for the O3 camera series of [ifm](https://www.ifm.com/), O3D3xx, O3X1xx and the O3R platform (OVP8xx along with the O3R22x cameras).

These examples showcase the use of the [ifm3d library](https://api.ifm3d.com/stable/).

## Supported languages

Currently, we support the following languages:
| Name   | Versions                   |
| ------ | -------------------------- |
| Python | 3.8, 3.9, 3.10, 3.11, 3.12 |
| C++    | GCC 7.5+, MSVC 2019+       |

## Compatibility

The examples have been tested in the following combination of versions:

| ifm3d-examples version | O3R firmware  | O3D firmware         | O3X firmware  | ifm3d library | Comment                                                                                                             |
| ---------------------- | ------------- | -------------------- | ------------- | ------------- | ------------------------------------------------------------------------------------------------------------------- |
| 1.2.1                  | 1.1.X, 1.4.X  | 1.71.9079, 1.80.8656 | 1.1.190       | 1.4.3, 1.5.3  | Additional examples for the O3D and O3X devices.                                                                    |
| 1.2.0                  | 1.1.30, 1.4.X | 1.71.9079, 1.80.8656 | 1.1.190       | 1.4.3, 1.5.3  | Support of the O3D3xx and O3X1xx examples                                                                           |
| 1.1.0                  | 1.1.30, 1.4.X | Not supported        | Not supported | 1.4.3, 1.5.3  | Some of the examples are only applicable to the O3R firmware version 1.4.X (for example, the IMU and CAN examples). |
| 1.0.0                  | 1.1.30        | Not supported        | Not supported | 1.4.3         |                                                                                                                     |
| 0.1.0                  | NA            | 1.80.8656, 1.71.9079 | 1.1.190       | 0.11.0        |                                                                                                                     |


Any other version might work but has not been explicitly tested.

## Prerequisites
To use these examples, you need to install the ifm3d library.

For the c++ library, follow the installation instructions on [api.ifm3d.com](https://api.ifm3d.com/stable/content/installation_instructions/index.html).

For the Python library, install using pip: `pip install ifm3dpy`.

For more details refer to [the ifm3d documentation on api.ifm3d.com](https://api.ifm3d.com/stable/index.html).

## common

This folder contains examples that apply to the three device types: the O3R perception platform, the O3X1xx and the O3D3xx cameras.

## o3d3xx-o3x1xx

This folder contains examples for the O3D3XX and the O3X1XX camera series, in Python and C++.

## ovp8xx

This folder contains examples for the O3R platform, which is composed of an OVP8xx compute unit and one or more O3R22x camera.

## Getting Started

To get started with this project, follow the instructions below:

1. Clone the repository.
2. Navigate to common, o3d3xx-o3x1xx or ovp8xx, depending on the device you are interested in.
3. Choose a programming language and the example that aligns with your requirements.
4. Follow the instructions provided in the example's README file to set up and run the example, or open up the example file to read through the relevant setup.

Most of the examples are amply commented out and sections that should be adapted to the user's specific setup are marked in the code.

## Contributing

Contributions are welcome! If you have any improvements or additional examples to share, please submit a pull request. 

## License

This project is licensed under the Apache version 2.0 license. See the [LICENSE FILE](./LICENSE) for more details.
