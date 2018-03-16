
ifm3d Examples
==============
This project is formerly the `examples` sub-module of the
[ifm3d](https://github.com/lovepark/ifm3d) project. It has been moved to a
standalone project to increase its efficacy as a teaching tool. Specifically,
beyond providing concrete code examples for interfacing to `ifm3d` it also
shows how to integrate `ifm3d` into an external project via `cmake`. This
project relies upon `ifm3d` version 0.9.0 or better. The remainder of the old
`README` now follows -- with minor edits.

This directory contains example programs that utilize `ifm3d`. The
intention is to create standalone programs that illustrate one very specific
concept in order to serve the purpose of letting developers ramp up quickly
with using the library. The build infrastructure in this directory is minimal
and the programs are intended to be run in place. Additonally, unless
specifically stated otherwise, things like performance and robust error
handling are not demonstrated. The purpose is to clearly illustrate the task
without clouding it with the details of real-world software engineering --
unless, of course, that was the point of the example.

It is expected that this library of examples will grow over time in response to
common themes we see on the issue tracker.

Building the examples
----------------------

Assuming you are starting from the top-level directory of this source
distribution:

    $ mkdir build
    $ cd build
    $ cmake ..
    $ make

What is included?
-----------------

* [ex-file_io](ex-file_io.cpp) Shows how to capture data from the camera and
  write the images to disk. In this example, the amplitude and radial distance
  image are written out as PNG files. We have removed the PCL-related example
  as we are in the process of deprecating our support for PCL from the `ifm3d`
  core.
* [ex-getmac](ex-getmac.cpp)
  Request the MAC address from the camera. The MAC address can be used as
  a unique identifier.
* [ex-timestamp](ex-timestamp.cpp)
 Request some frames from the camera and write the timestamps to stdout
* [ex-exposure_times](ex-exposure_times.cpp) Shows how to change imager
  exposure times on the fly while streaming in pixel data and validating the
  setting of the exposure times registered to the frame data.
* [ex-fast_app_switch](ex-fast_app_switch.cpp) Shows how to switch between two
  applications on the camera using PCIC
* [ex-pcicclient_async_messages](ex-pcicclient_async_messages.cpp) Shows how to
  use the PCICClient module to receive asynchronous notification (and error)
  messages from the camera.
* [ex-pcic_set_io](ex-pcic_set_io.cpp) Shows how to mutate the digial IO pins
  on the O3D camera by the PCIC interface.

LICENSE
-------
Please see the file called [LICENSE](LICENSE).
