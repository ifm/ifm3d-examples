/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
// This code example showcases how to retrieve a
// frame using the software trigger.
// The example applies to both the O3D and O3X
// devices.
// The O3X only allows a single connection, so
// any other application, for example the Vision
// Assistant, must be closed before running this example.

#include <chrono>
#include <cstdint>
#include <ifm3d/common/json_impl.hpp>
#include <ifm3d/common/logging/log.h>
#include <ifm3d/device.h>
#include <ifm3d/device/err.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <string>
#include <thread>

using namespace std::chrono_literals;

int main() {
  // Get the IP from the environment if defined
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  std::clog << "IP: " << IP << std::endl;

  //////////////////////////
  // Declare the objects
  //////////////////////////
  // Declare the device object
  auto device = ifm3d::Device::MakeShared(IP);
  // Enable the trigger mode.
  device->FromJSONStr(R"({"Apps":[{"TriggerMode":"2"}]})");

  auto fg = std::make_shared<ifm3d::FrameGrabber>(device);
  fg->Start({ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE});
  std::this_thread::sleep_for(1s); // Grace period after starting the data
                                   // stream

  // Trigger the frame acquisition. The frame will be
  // caught by the WaitForFrame function.
  fg->SWTrigger();
  auto future = fg->WaitForFrame();

  if (future.wait_for(3s) != std::future_status::ready) {
    std::cerr << "Timeout waiting for camera!" << std::endl;
    return -1;
  }
  auto frame = future.get();

  auto distance = frame->GetBuffer(ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE);
  std::cout << "Sample data from the frame, at index [50, 50]: " << std::endl;
  std::cout << distance.at<float>(50, 50) << std::endl;

  return 0;
}
