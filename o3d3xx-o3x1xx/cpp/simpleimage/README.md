# ifm3d - Simple Image Container

`ifm3d`, through its modularity, also encourages the
creation of new image containers to be utilized within the overall `ifm3d`
ecosystem. The interface is explained is very well in
[ifm3d image conatiners](https://github.com/ifm/ifm3d/blob/master/doc/img_container.md)

`simpleimage` container is an header only interface for ifm3d lib which is independent of any third party library.
Following are the structure used in this module for storing image, point and pointClouds
**Image**

```c++
struct Img
  {
    std::vector<std::uint8_t> data;
    int width;
    int height;
    pixel_format format;
  };
```

**point**

```c++
  struct Point
  {
    float x;
    float y;
    float z;
  };
```

**pointCloud**

```c++
 struct PointCloud
 {
   std::vector<Point> points;
   int width;
   int height;
 };
```

[pixel_format](https://github.com/ifm/ifm3d/blob/master/modules/framegrabber/include/ifm3d/fg/byte_buffer.h)

The example in this modules explains how to grab the data from the ifm 3d devices and saved a .ppm image using [ppm-io](https://github.com/thinks/ppm-io) module. To save the images the data is scaled to uint8 format. Amplitude image data is scaled by the minimum and maximum value in the grabbed amplitude data, whereas for Distance image the data is scaled in distance range from 0.0m to 2.5m, which means the data values after 2.5m will be shown as 255.

simpleimage module is configured in such a way that it can be build outside ifm3d-example repository which can be helpful for build applications which do not want to add OPenCV or PCL as a dependency.

If you have questions, feel free to ask on our
[issue tracker](https://github.com/ifm/ifm3d/issues).
