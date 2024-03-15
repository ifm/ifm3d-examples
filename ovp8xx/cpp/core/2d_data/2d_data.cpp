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
  cv::startWindowThread();
  while (true){
    if (!img_queue.empty()) {
      cv::imshow("RGB Image", cv::imdecode(img_queue.front(), cv::IMREAD_UNCHANGED));
      img_queue.pop();
      cv::waitKey(1);
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }
}

void Callback(ifm3d::Frame::Ptr frame) {
  auto rgb_img = frame->GetBuffer(ifm3d::buffer_id::JPEG_IMAGE);
  // For displaying the data, make sure to use to copy method.
  // This ensure the data is still available for display after the callback has returned.
  auto rgb_cv = ConvertImageToMatCopy(rgb_img);
  // No copy conversion of the image to cv::Mat:
  // auto rgb_cv = ConvertImageToMatNoCopy(rgb_img);
  // Push image to queue for display
  img_queue.push(rgb_cv);
}

int main() {
  // Get the IP from the environment if defined
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP") : ifm3d::DEFAULT_IP.c_str();
  std::clog << "IP: " << IP << std::endl;

  //////////////////////////
  // Declare the O3R object
  //////////////////////////
  // Declare the device object (one object only, corresponding to the VPU)
  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  //////////////////////////
  // Pick a 2D port to use
  //////////////////////////
  // Pick the first available 2D port.
  uint16_t pcic_port = 0;
  for (const auto &port : o3r->Ports()) {
    if (port.type == "2D") {
      std::cout << "Using first available 2D port: " << port.port << std::endl;
      pcic_port = port.pcic_port;
      break;
    }
  }
  
  // Alternatively, manually pick the port 
  // corresponding to your 2D camera
  // std::string port_nb = "port0";
  // if (o3r->Port(port_nb).type != "2D") {
  //   std::cerr << "Please provide a 2D port number." << std::endl;  
  //   return -1;
  // }
  // uint16_t pcic_port = o3r->Port(port_nb).pcic_port;

  // Verify that a correct port number was provided
  if (pcic_port == 0) {
    std::cerr << "No 2D port found in the configuration," << std::endl;
    return -1;
  }
  //////////////////////////
  // Declare the FrameGrabber object
  //////////////////////////
  auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, pcic_port);

  //////////////////////////
  // Get a frame:
  //////////////////////////
  fg->OnNewFrame(&Callback);
  fg->Start({ifm3d::buffer_id::JPEG_IMAGE});

  Display();

  fg->Stop();
  return 0;
}
