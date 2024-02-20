/*
 * Copyright 2022-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <chrono>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <ifm3d/fg/buffer.h>
#include <ifm3d/fg/distance_image_info.h>
#include <iostream>
#include <opencv2/core/core.hpp>
#include <opencv2/core/mat.hpp>
#include <opencv2/highgui.hpp>
#include <opencv2/opencv.hpp>
#include <queue>
#include <string>
#include <thread>

// LUT for image format conversion
static std::unordered_map<ifm3d::pixel_format, int> LUT_TYPE{
    {ifm3d::pixel_format::FORMAT_8U, CV_8U},
    {ifm3d::pixel_format::FORMAT_8S, CV_8S},
    {ifm3d::pixel_format::FORMAT_16U, CV_16U},
    {ifm3d::pixel_format::FORMAT_16S, CV_16S},
    {ifm3d::pixel_format::FORMAT_32S, CV_32S},
    {ifm3d::pixel_format::FORMAT_32F, CV_32F},
    {ifm3d::pixel_format::FORMAT_32F3, CV_32F},
    {ifm3d::pixel_format::FORMAT_64F, CV_64F}};
// LUT for image format size
static std::unordered_map<ifm3d::pixel_format, int> LUT_SIZE{
    {ifm3d::pixel_format::FORMAT_8U, 1},
    {ifm3d::pixel_format::FORMAT_8S, 1},
    {ifm3d::pixel_format::FORMAT_16U, 2},
    {ifm3d::pixel_format::FORMAT_16S, 2},
    {ifm3d::pixel_format::FORMAT_32S, 4},
    {ifm3d::pixel_format::FORMAT_32F, 4},
    {ifm3d::pixel_format::FORMAT_32F3, 4},
    {ifm3d::pixel_format::FORMAT_64F, 8}};

// Converts ifm3d::Buffer to cv:Mat.
// cv::Mat will not take ownership of the data.
// Make sure ifm3d::Buffer is not destroyed while the cv::Mat is still around.
cv::Mat ConvertImageToMatNoCopy(ifm3d::Buffer &img) {
  return cv::Mat(img.height(), img.width(), LUT_TYPE[img.dataFormat()],
                 img.ptr(0));
}

// Converts ifm3d::Buffer to cv:Mat.
// This function copies the data so that
// you can safely dispose of the ifm3d::Buffer.
cv::Mat ConvertImageToMatCopy(ifm3d::Buffer &img) {
  auto mat = cv::Mat(img.height(), img.width(), LUT_TYPE[img.dataFormat()]);
  std::memcpy(mat.data, img.ptr(0),
              img.width() * img.height() * LUT_SIZE[img.dataFormat()]);
  return mat;
}

std::queue<cv::Mat> img_queue;

void Display() {
  if (img_queue.empty()) {
    return;
  }
  cv::startWindowThread();
  cv::imshow("RGB Image", cv::imdecode(img_queue.front(), cv::IMREAD_UNCHANGED));
  img_queue.pop();
  cv::waitKey(1);
}

void Callback(ifm3d::Frame::Ptr frame) {
  auto rgb_img = frame->GetBuffer(ifm3d::buffer_id::JPEG_IMAGE);
  // No copy conversion of the image to cv::Mat:
  auto rgb_cv = ConvertImageToMatNoCopy(rgb_img);
  // Alternatively, use:
  // auto rgb_cv = ConvertImageToMatCopy(rgb_img);
  // Push image to queue for display
  img_queue.push(rgb_cv);
}

int main() {

  //////////////////////////
  // Declare the objects:
  //////////////////////////
  // Declare the device object (one object only, corresponding to the VPU)
  auto o3r = std::make_shared<ifm3d::O3R>();
  // Declare the FrameGrabber object.
  const auto PCIC_PORT = o3r->Port("port2").pcic_port;
  auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, PCIC_PORT);

  std::cout << std::to_string(PCIC_PORT) << std::endl;

  //////////////////////////
  // Get a frame:
  //////////////////////////
  fg->OnNewFrame(&Callback);
  fg->Start({ifm3d::buffer_id::JPEG_IMAGE});
  auto start = std::chrono::steady_clock::now();
  do{
    Display();
  } while (std::chrono::steady_clock::now() - start <
             std::chrono::seconds(10));
  fg->Stop();
  return 0;
}
