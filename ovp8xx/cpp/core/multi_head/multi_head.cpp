/*
 * Copyright 2021-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

/*How to: receive data from multiple heads
 One feature of the O3R platform is to enable the use of multiple camera heads
 of different types (2D, 3D, various resolutions, etc). In this example, we
 show how to retrieve the pcic port number for each head connected to the VPU
 along with its type, create `FrameGrabber` objects and get a frame for each.
*/
#include <chrono>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iomanip>
#include <iostream>

using namespace std::chrono_literals;

// This function formats the timestamps for proper display
// a.k.a converts to local time
std::string formatTimestamp(ifm3d::TimePointT timestamp) {
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

int main() {

  // Declare the O3R object
  // Get the IP from the environment if defined
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  std::clog << "IP: " << IP << std::endl;

  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  // Retrieve ports configuration
  ifm3d::json conf = o3r->Get();

  // Initialize the structures
  std::vector<ifm3d::FrameGrabber::Ptr> fgs;

  std::cout << "Available connections:" << std::endl;

  for (const auto &port : conf["ports"].items()) {
    // exclude port 6, since it is the IMU port
    if (port.key() != "port6") {
      // Create lists of connected PCIC ports along with types
      ifm3d::json::json_pointer p1("/ports/" + port.key() +
                                   "/data/pcicTCPPort");
      const auto pcic = conf[p1];
      ifm3d::json::json_pointer p2("/ports/" + port.key() +
                                   "/info/features/type");
      const auto type = conf[p2];
      // Display connected port with type
      std::cout << "Port: " << port.key() << "\t PCIC: " << pcic
                << "\t Type: " << type << std::endl;
      // Create list of FrameGrabber and ImageBuffer objects for connected
      // ports
      auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, pcic);

      // Start the framegrabber
      if (type == "2D") {
        fg->Start({ifm3d::buffer_id::JPEG_IMAGE});
      } else if (type == "3D") {
        fg->Start({ifm3d::buffer_id::XYZ});
      } else {
        std::cerr << "Unknown type!" << std::endl;
      }
      fgs.push_back(fg);
    }
  }

  // Grab frames from each heads
  // The timestamp has two parts, the timestamp in seconds and the timestamp in
  // nanoseconds
  for (auto fg : fgs) {
    auto future = fg->WaitForFrame();
    if (future.wait_for(3s) != std::future_status::ready) {
      std::cerr << "Timeout waiting for camera!" << std::endl;
      return -1;
    }
    auto frame = future.get();
    std::cout << "Timestamp of frame " << std::setw(2) << std::setfill('0')
              << ": " << formatTimestamp(frame->TimeStamps()[0]) << std::endl;

    fg->Stop();
  }

  return 0;
}
