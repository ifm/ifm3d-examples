/*
 * Copyright 2021-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <chrono>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <thread>

using namespace ifm3d::literals;

int main() {

  // Declare the device object (one object only, corresponding to the VPU)
  auto dev = std::make_shared<ifm3d::O3R>();
  // Declare the FrameGrabber
  // One FrameGrabber per camera head (define the port number).
  const auto pcic_port = dev->Port("port2").pcic_port;
  auto fg = std::make_shared<ifm3d::FrameGrabber>(dev, pcic_port);

  // Set Schema and start the grabber
  fg->Start({ifm3d::buffer_id::NORM_AMPLITUDE_IMAGE,
             ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE, ifm3d::buffer_id::XYZ,
             ifm3d::buffer_id::CONFIDENCE_IMAGE});
  //////////////////////////
  // use framegrabber in streaming mode
  //////////////////////////
  fg->OnNewFrame([&](ifm3d::Frame::Ptr frame) {
    auto distance_image = frame->GetBuffer(ifm3d::buffer_id::CONFIDENCE_IMAGE);
    std::cout << distance_image.width() << std::endl;
    // This is playground area for user to play with ifm3d Buffers
  });

  std::this_thread::sleep_for(std::chrono::seconds(10));
  fg->Stop();

  return 0;
}
