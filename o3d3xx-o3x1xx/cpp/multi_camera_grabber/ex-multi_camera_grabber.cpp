/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
//
// ex-multi_camera_grabber.cpp
//
// Capture frames from multiple ifm 3D cameras which are configured to be
// triggered through software, and display the time stamp of the frame received.
// also measure the time taken to receive the set of frames.
//
// Prerequisites:
// 1) Each ifm 3D camera should be configured to use "Process Interface" for
// trigger. 2) You Should be able to ping each of the 3D camera from the PC on
// which this code executes. 3) Incase your network uses a proxy, you will need
// to configure your system to bypass the proxy for the used IP's.
//

#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <memory>
#include <sstream>
#include <vector>

#include <ifm3d/device/device.h>
#include <ifm3d/device/legacy_device.h>
#include <ifm3d/fg.h>

namespace {
// List of camera devices to be used for grabbing.
std::vector<std::string> camera_ip_list = {"192.168.0.68", "192.168.0.80"};

// Utility function to format the timestamp
std::string formatTimestamp(ifm3d::TimePointT timestamp) {
  std::time_t time = std::chrono::system_clock::to_time_t(
      std::chrono::time_point_cast<std::chrono::system_clock::duration>(
          timestamp));

  std::chrono::milliseconds milli =
      std::chrono::duration_cast<std::chrono::milliseconds>(
          timestamp.time_since_epoch() -
          std::chrono::duration_cast<std::chrono::seconds>(
              timestamp.time_since_epoch()));

  std::ostringstream s;
  s << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S") << ":"
    << std::setw(3) << std::setfill('0') << milli.count();

  return s.str();
}
} // namespace

int main(int argc, const char **argv) {
  std::chrono::system_clock::time_point start, end;

  // vector of objects
  std::vector<ifm3d::Device::Ptr> devices;
  std::vector<ifm3d::FrameGrabber::Ptr> grabbers;
  ifm3d::json config;

  for (const auto &camera_ip : camera_ip_list) {
    auto cam = ifm3d::Device::MakeShared(camera_ip);
    devices.push_back(cam);

    // Create a frame grabber object
    grabbers.push_back(std::make_shared<ifm3d::FrameGrabber>(cam));
    auto legacy_device = std::dynamic_pointer_cast<ifm3d::LegacyDevice>(cam);

    // mark the current active application as sw triggered
    int idx = legacy_device->ActiveApplication();
    config = legacy_device->ToJSON();
    config["ifm3d"]["Apps"][idx - 1]["TriggerMode"] =
        std::to_string(static_cast<int>(ifm3d::Device::trigger_mode::SW));
    legacy_device->FromJSON(config);
  }

  // grab the frames from the multiple cameras
  int frame_count = 10;
  for (int i = 0; i < frame_count; i++) {
    start = std::chrono::system_clock::now();
    uint8_t id = 0;
    for (const auto &camera_ip : camera_ip_list) {
      auto fg = grabbers.at(id);
      // use SWtrigger
      std::cout << "SW trigger for camera(" << camera_ip << ")" << std::endl;
      fg->Start({ifm3d::buffer_id::AMPLITUDE_IMAGE});
      fg->SWTrigger();
      auto frame = fg->WaitForFrame();
      if (frame.wait_for(std::chrono::milliseconds(1000)) !=
          std::future_status::ready) {
        std::cerr << "timeout waiting for camera(" << camera_ip << ") frame"
                  << std::endl;
        return -1;
      } else {
        ifm3d::TimePointT timestamp = frame.get()->TimeStamps().front();
        std::cout << "got camera(" << camera_ip << ") frame timestamp "
                  << std::setw(2) << std::setfill('0') << ":"
                  << formatTimestamp(timestamp) << std::endl;
      }
      id++;
    }
    end = std::chrono::system_clock::now();
    std::chrono::duration<double, std::milli> duration_ms = (end - start);
    std::cout << "total time taken to receive in ms " << duration_ms.count()
              << " ms" << std::endl;
  }
  return 0;
}
