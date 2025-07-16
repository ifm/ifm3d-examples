/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

// ex-timestamp.cpp
// Request some frames from the camera and write the timestamps to stdout

#include <cstdlib>
#include <fmt/core.h>
#include <iomanip>
#include <iostream>
#include <sstream>

#include <ifm3d/device/device.h>
#include <ifm3d/fg.h>

std::string formatTimestamp(ifm3d::TimePointT timestamp) {
  /**
   * This function formats the timestamps for proper display
   * a.k.a converts to local time
   */
  using namespace std::chrono;
  std::time_t time = std::chrono::system_clock::to_time_t(
      std::chrono::time_point_cast<std::chrono::system_clock::duration>(
          timestamp));

  milliseconds milli = duration_cast<milliseconds>(
      timestamp.time_since_epoch() -
      duration_cast<seconds>(timestamp.time_since_epoch()));

  std::ostringstream s;
  s << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S") << ":"
    << std::setw(3) << std::setfill('0') << milli.count();

  return s.str();
}

int main(int argc, char *argv[]) {
  int frame_count = 10;

  auto cam = ifm3d::Device::MakeShared();

  auto fg = std::make_shared<ifm3d::FrameGrabber>(cam);

  fg->Start({});

  for (size_t i = 0; i < frame_count; i++) {
    auto frame = fg->WaitForFrame();
    if (frame.wait_for(std::chrono::milliseconds(1000)) !=
        std::future_status::ready) {
      std::cerr << "Timeout waiting for camera!" << std::endl;
      continue;
    }
    auto timestamp = frame.get()->TimeStamps().front();
    std::cout << "Timestamp of frame " << std::setw(2) << std::setfill('0')
              << (i + 1) << ":" << formatTimestamp(timestamp) << std::endl;
  }

  fg->Stop();
  return 0;
}
