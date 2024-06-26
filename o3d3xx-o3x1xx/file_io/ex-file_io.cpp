/*
 * Copyright (C) 2016 Love Park Robotics, LLC
 * Copyright (C) 2017 ifm syntron gmbh
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

//
// ex-file_io.cpp
//
// Capture a frame from the camera, and write the data out to files. For
// exemplary purposes, we will write the amplitdue and radial distance images
// to PNG files.
//

#include <iostream>
#include <memory>

#include <opencv2/core/mat.hpp>
#include <opencv2/opencv.hpp>
#include <opencv2/highgui/highgui_c.h>
#include <ifm3d/device/device.h>
#include <ifm3d/fg.h>

template <typename T>
cv::Mat createMat(T* data, int rows, int cols, int chs = 1) {
    // Create Mat from buffer
    cv::Mat mat(rows, cols, CV_MAKETYPE(cv::DataType<T>::type, chs));
    memcpy(mat.data, data, rows*cols*chs * sizeof(T));
    return mat;
}

int main(int argc, const char **argv)
{
  auto cam = ifm3d::Device::MakeShared();

  ifm3d::FrameGrabber::Ptr fg = std::make_shared<ifm3d::FrameGrabber>(cam);

  fg->Start({ifm3d::buffer_id::NORM_AMPLITUDE_IMAGE,ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE});

  auto frame = fg->WaitForFrame();
  if (frame.wait_for(std::chrono::milliseconds(1000)) != std::future_status::ready)
    {
      std::cerr << "Timeout waiting for camera!" << std::endl;
      return -1;
    }

  auto amplitude = frame.get()->GetBuffer(ifm3d::buffer_id::NORM_AMPLITUDE_IMAGE);
  cv::imwrite("amplitude.png", createMat<uint8_t>(amplitude.ptr(0),amplitude.height(),amplitude.width(),1));

return 0;
}


