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

#ifndef __IFM3D_SIMPLEIMAGE_DETAIL_SIMPLEIMAGE_BUFFER_HPP__
#define __IFM3D_SIMPLEIMAGE_DETAIL_SIMPLEIMAGE_BUFFER_HPP__

#include <cstdint>
#include <unordered_map>
#include <vector>
#include <ifm3d/fg/byte_buffer.h>


//==============================================
// simpleImage Buffer implementation
//==============================================

ifm3d::SimpleImageBuffer::SimpleImageBuffer()
  : ifm3d::ByteBuffer<ifm3d::SimpleImageBuffer>()
{ }

ifm3d::SimpleImageBuffer::~SimpleImageBuffer() = default;

// move ctor
ifm3d::SimpleImageBuffer::SimpleImageBuffer(ifm3d::SimpleImageBuffer&& src_buff)
  : ifm3d::SimpleImageBuffer::SimpleImageBuffer()
{
  this->SetBytes(src_buff.bytes_, false);
}

// move assignment
ifm3d::SimpleImageBuffer&
ifm3d::SimpleImageBuffer::operator= (ifm3d::SimpleImageBuffer&& src_buff)
{
  this->SetBytes(src_buff.bytes_, false);
  return *this;
}

// copy ctor
ifm3d::SimpleImageBuffer::SimpleImageBuffer(const ifm3d::SimpleImageBuffer& src_buff)
  : ifm3d::SimpleImageBuffer::SimpleImageBuffer()
{
  this->SetBytes(const_cast<std::vector<std::uint8_t>&>(src_buff.bytes_),
                 true);
}

// copy assignment
ifm3d::SimpleImageBuffer&
ifm3d::SimpleImageBuffer::operator= (const ifm3d::SimpleImageBuffer& src_buff)
{
  if (this == &src_buff)
    {
      return *this;
    }

  this->SetBytes(const_cast<std::vector<std::uint8_t>&>(src_buff.bytes_),
                 true);
  return *this;
}

ifm3d::SimpleImageBuffer::Img
ifm3d::SimpleImageBuffer::DistanceImage()
{
  this->Organize();
  return this->dist_;
}

ifm3d::SimpleImageBuffer::Img
ifm3d::SimpleImageBuffer::UnitVectors()
{
  this->Organize();
  return this->uvec_;
}

ifm3d::SimpleImageBuffer::Img
ifm3d::SimpleImageBuffer::GrayImage()
{
  this->Organize();
  return this->gray_;
}

ifm3d::SimpleImageBuffer::Img
ifm3d::SimpleImageBuffer::AmplitudeImage()
{
  this->Organize();
  return this->amp_;
}

ifm3d::SimpleImageBuffer::Img
ifm3d::SimpleImageBuffer::RawAmplitudeImage()
{
  this->Organize();
  return this->ramp_;
}

ifm3d::SimpleImageBuffer::Img
ifm3d::SimpleImageBuffer::ConfidenceImage()
{
  this->Organize();
  return this->conf_;
}

ifm3d::SimpleImageBuffer::Img
ifm3d::SimpleImageBuffer::XYZImage()
{
  this->Organize();
  return this->xyz_;
}

template <typename T>
void
ifm3d::SimpleImageBuffer::ImCreate(ifm3d::image_chunk im,
                              std::uint32_t fmt,
                              std::size_t idx,
                              std::uint32_t width,
                              std::uint32_t height,
                              int nchan,
                              std::uint32_t npts,
                              const std::vector<std::uint8_t>& bytes)
{
  Img *img;
  switch (im)
    {
    case ifm3d::image_chunk::CONFIDENCE:
      img = &this->conf_;
      break;

    case ifm3d::image_chunk::AMPLITUDE:
      img = &this->amp_;
      break;

    case ifm3d::image_chunk::RADIAL_DISTANCE:
      img = &this->dist_;
      break;

    case ifm3d::image_chunk::UNIT_VECTOR_ALL:
      img = &this->uvec_;
      break;

    case ifm3d::image_chunk::RAW_AMPLITUDE:
      img = &this->ramp_;
      break;

    case ifm3d::image_chunk::GRAY:
      img = &this->gray_;
      break;

    default:
      return;
    }

	std::size_t incr = sizeof(T) * nchan;
	img->data.resize(sizeof(T)*nchan*width*height);
    img->format = static_cast<pixel_format>(fmt);
    img->width = width;
    img->height = height;
    

   for (std::size_t i = 0; i < (npts*nchan); i++ )
      {
        const std::uint8_t* src = bytes.data() + idx + (i * sizeof(T));
        std::uint8_t* dst = img->data.data() + (i * sizeof(T));

        copy_data<T>(src, dst);
      }
}

template <typename T>
void
ifm3d::SimpleImageBuffer::CloudCreate(std::uint32_t fmt,
                                 std::size_t xidx,
                                 std::size_t yidx,
                                 std::size_t zidx,
                                 std::uint32_t width,
                                 std::uint32_t height,
                                 std::uint32_t npts,
                                 const std::vector<std::uint8_t>& bytes)
{
   std::size_t incr = sizeof(T);
	Img *img = &this->xyz_;
	img->data.resize(3*npts*incr);
    img->format = static_cast<pixel_format>(fmt);
    img->width = width;
    img->height = height;
	PointCloud *cloud = &this->cloud_;
    cloud->width = width;
    cloud->height = height;
    cloud->points.resize(npts);

	T x_, y_, z_;

    // We assume, if the data from the sensor are a floating point type,
    // the data are in meters, otherwise, the sensor is sending an
    // integer type and the data are in mm.
    bool convert_to_meters = true;
    if ((img->format == pixel_format::FORMAT_32F) || (img->format == pixel_format::FORMAT_64F))
      {
        convert_to_meters = false;
      }

    for (std::size_t i = 0; i < npts;  i++, xidx += incr, yidx += incr, zidx += incr)
    {
        Point& pt = cloud->points[i];

        // convert to ifm3d coord frame
        x_ = ifm3d::mkval<T>(bytes.data()+zidx);
        y_ = -ifm3d::mkval<T>(bytes.data()+xidx);
        z_ = -ifm3d::mkval<T>(bytes.data()+yidx);

        copy_data<T>(bytes.data() + zidx, img->data.data() + 3 * i * incr);
        copy_data<T>(bytes.data() + xidx, img->data.data() + 3 * i * incr + incr);
        copy_data<T>(bytes.data() + yidx, img->data.data() + 3 * i * incr + (2 * incr));

        if (convert_to_meters)
        {
            pt.x = x_ / 1000.0f;
            pt.y = y_ / 1000.0f;
            pt.z = z_ / 1000.0f;
        }
        else
        {
            pt.x = x_;
            pt.y = y_;
            pt.z = z_;
        }
    }
}

#endif // __IFM3D_SIMPLEIMAGE_DETAIL_SIMPLEIMAGE_BUFFER_HPP__
