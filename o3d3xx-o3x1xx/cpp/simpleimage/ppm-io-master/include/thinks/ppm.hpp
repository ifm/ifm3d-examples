// Copyright 2018 Tommy Hinks
//
// Permission is hereby granted, free of charge, to any person obtaining a
// copy of this software and associated documentation files (the "Software"),
// to deal in the Software without restriction, including without limitation
// the rights to use, copy, modify, merge, publish, distribute, sublicense,
// and/or sell copies of the Software, and to permit persons to whom the
// Software is furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in
// all copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
// FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
// DEALINGS IN THE SOFTWARE.

#ifndef THINKS_PPM_PPM_HPP_INCLUDED
#define THINKS_PPM_PPM_HPP_INCLUDED

#include <cassert>
#include <cstdint>
#include <exception>
#include <fstream>
#include <sstream>
#include <string>
#include <vector>

namespace thinks {
namespace ppm {
namespace detail {

template <typename F>
inline F openFileStream(std::string const& filename,
                        std::ios_base::openmode const mode = std::ios::binary) {
  using namespace std;

  auto ofs = F(filename, mode);
  if (ofs.fail()) {
    auto ss = stringstream();
    ss << "cannot open file '" << filename << "'";
    throw runtime_error(ss.str());
  }

  return ofs;
}

}  // namespace detail

//! Read a PPM image from an input stream.
//!
//! Assumptions:
//! - the PPM header does not contain any comments.
//! - the PPM header width and height are non-zero.
//! - the input pointers are non-null.
//!
//! Pixel data is read as RGB triplets in row major order. For instance,
//! the pixel data for a 2x2 image is represented as follows:
//!
//!       | Column 0                         | Column 1
//!       +----------------------------------+------------------------------------+
//! Row 0 | RGB: {data[0], data[1], data[2]} | RGB: {data[3], data[4], data[5]}
//! |
//!       +----------------------------------+------------------------------------+
//! Row 1 | RGB: {data[6], data[7], data[8]} | RGB: {data[9], data[10],
//! data[11]} |
//!       +----------------------------------+------------------------------------+
//!
//! An std::runtime_error is thrown if:
//! - the magic number is not 'P6'.
//! - the max value is not '255'.
//! - the pixel data cannot be read.
inline void readRgbImage(std::istream& is, std::size_t* width,
                         std::size_t* height,
                         std::vector<std::uint8_t>* pixel_data) {
  using namespace std;

  assert(width != nullptr);
  assert(height != nullptr);
  assert(pixel_data != nullptr);

  // Read header.
  auto const expected_magic_number = string("P6");
  auto const expected_max_value = string("255");
  auto magic_number = string();
  auto max_value = string();
  is >> magic_number >> *width >> *height >> max_value;

  assert(*width != 0);
  assert(*height != 0);

  if (magic_number != expected_magic_number) {
    auto ss = stringstream();
    ss << "magic number must be '" << expected_magic_number << "'";
    throw runtime_error(ss.str());
  }

  if (max_value != expected_max_value) {
    auto ss = stringstream();
    ss << "max value must be " << expected_max_value;
    throw runtime_error(ss.str());
  }

  // Skip ahead (an arbitrary number!) to the pixel data.
  is.ignore(256, '\n');

  // Read pixel data.
  pixel_data->resize((*width) * (*height) * 3);
  is.read(reinterpret_cast<char*>(pixel_data->data()), pixel_data->size());

  if (!is) {
    auto ss = stringstream();
    ss << "failed reading " << pixel_data->size() << " bytes";
    throw runtime_error(ss.str());
  }
}

//! See std::istream overload version above.
//!
//! Throws an std::runtime_error if file cannot be opened.
inline void readRgbImage(std::string const& filename, std::size_t* width,
                         std::size_t* height,
                         std::vector<std::uint8_t>* pixel_data) {
  auto ifs = detail::openFileStream<std::ifstream>(filename);
  readRgbImage(ifs, width, height, pixel_data);
  ifs.close();
}

//! Write a PPM image to an output stream.
//!
//! Pixel data is given as RGB triplets in row major order. For instance,
//! the pixel data for a 2x2 image is represented as follows:
//!
//!       | Column 0                         | Column 1
//!       +----------------------------------+------------------------------------+
//! Row 0 | RGB: {data[0], data[1], data[2]} | RGB: {data[3], data[4], data[5]}
//! |
//!       +----------------------------------+------------------------------------+
//! Row 1 | RGB: {data[6], data[7], data[8]} | RGB: {data[9], data[10],
//! data[11]} |
//!       +----------------------------------+------------------------------------+
//!
//! An std::runtime_error is thrown if:
//! - width or height is zero.
//! - the size of the pixel data does not match the width and height.
inline void writeRgbImage(std::ostream& os, std::size_t const width,
                          std::size_t const height,
                          std::vector<std::uint8_t> const& pixel_data) {
  using namespace std;

  if (width == 0) {
    throw runtime_error("width must be non-zero");
  }

  if (height == 0) {
    throw runtime_error("height must be non-zero");
  }

  if (pixel_data.size() != width * height * 3) {
    throw runtime_error("pixel data must match width and height");
  }

  // Write header.
  auto const magic_number = string("P6");
  auto const max_value = string("255");
  os << magic_number << "\n"
     << width << " " << height << "\n"
     << max_value << "\n";  // Marks beginning of pixel data.

  // Write pixel data.
  os.write(reinterpret_cast<char const*>(pixel_data.data()), pixel_data.size());
}

//! See std::ostream overload version above.
//!
//! Throws an std::runtime_error if file cannot be opened.
inline void writeRgbImage(std::string const& filename, std::size_t const width,
                          std::size_t const height,
                          std::vector<std::uint8_t> const& pixel_data) {
  auto ofs = detail::openFileStream<std::ofstream>(filename);
  writeRgbImage(ofs, width, height, pixel_data);
  ofs.close();
}

}  // namespace ppm
}  // namespace thinks

#endif  // THINKS_PPM_PPM_HPP_INCLUDED
