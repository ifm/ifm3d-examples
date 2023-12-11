// -*- c++ -*-
/*
 * Copyright (C) 2018 ifm electronic, gmbh
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distribted on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef __IFM3D_SIMPLEIMAGE_SIMPLEIMAGEBUFFER_BUFFER_H__
#define __IFM3D_SIMPLEIMAGE_SIMPLEIMAGEBUFFER_BUFFER_H__

#include <cstdint>
#include <memory>
#include <vector>
#include <ifm3d/fg/byte_buffer.h>

namespace ifm3d
{
  /** copy the sizeof(T) bytes frm src to dst byte buffer. 
   * Given that the ifm sensors transmit data in little endian
   * format, this function will swap bytes if necessary for the host
   * representation of T param
   */
	
  template<typename T>
  void copy_data(const std::uint8_t* src, std::uint8_t* dst)
  {
	#if !defined(_WIN32) && __BYTE_ORDER == __BIG_ENDIAN
    std::reverse_copy(src, src + sizeof(T), dst);
	#else
    std::copy(src,  src + sizeof(T), dst);
	#endif
  }
  class SimpleImageBuffer : public ifm3d::ByteBuffer<ifm3d::SimpleImageBuffer>
  {
  public:
  
  struct Img
  {
    std::vector<std::uint8_t> data;
    int width;
    int height;
    pixel_format format;
  };

  struct Point
  {
    float x;
    float y;
    float z;
  };

  struct PointCloud
  {
    std::vector<Point> points;
    int width;
    int height;
  };
   
    friend class ifm3d::ByteBuffer<ifm3d::SimpleImageBuffer>;
    using Ptr = std::shared_ptr<SimpleImageBuffer>;

    // ctor/dtor
    SimpleImageBuffer();
    ~SimpleImageBuffer();

    // move semantics
    SimpleImageBuffer(SimpleImageBuffer&&);
    SimpleImageBuffer& operator=(SimpleImageBuffer&&);

    // copy semantics
    SimpleImageBuffer(const SimpleImageBuffer& src_buff);
    SimpleImageBuffer& operator=(const SimpleImageBuffer& src_buff);

    // accessors
   /**
   * Accessor for the wrapped radial distance image
   */
  Img DistanceImage();

  /**
   * Accessor for the wrapped unit vectors
   */
  Img UnitVectors();

  /**
   * Accessor the the wrapped ambient light image
   */
  Img GrayImage();

  /**
   * Accessor for the normalized amplitude image
   */
  Img AmplitudeImage();

  /**
   * Accessor for the raw amplitude image
   */
  Img RawAmplitudeImage();

  /**
   * Accessor for the confidence image
   */
  Img ConfidenceImage();

  /**
   * Accessor for the image encoding of the point cloud
   *
   * 3-channel image of spatial planes X, Y, Z
   */
  Img XYZImage();

  /**
   * Returns the point cloud
   */
  PointCloud Cloud();


  protected:
    template <typename T>
    void ImCreate(ifm3d::image_chunk im,
                  std::uint32_t fmt,
                  std::size_t idx,
                  std::uint32_t width,
                  std::uint32_t height,
                  int nchan,
                  std::uint32_t npts,
                  const std::vector<std::uint8_t>& bytes);

    template <typename T>
    void CloudCreate(std::uint32_t fmt,
                     std::size_t xidx,
                     std::size_t yidx,
                     std::size_t zidx,
                     std::uint32_t width,
                     std::uint32_t height,
                     std::uint32_t npts,
                     const std::vector<std::uint8_t>& bytes);
  private:
  Img dist_;
  Img uvec_;
  Img gray_;
  Img amp_;
  Img ramp_;
  Img conf_;
  Img xyz_;
  PointCloud cloud_;

  }; // end: class SimpleImageBuffer
} // end: namespace ifm3d

#include <ifm3d/simpleimage/detail/simpleimage_buffer.hpp>

#endif // __IFM3D_SIMPLEIMAGE_SIMPLEIMAGEBUFFER_BUFFER_H__
