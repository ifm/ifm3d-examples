/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

// This examples shows how to use the deserializer module
// to extract data from the TOFInfoV4 buffer.

#include <chrono>
#include <ifm3d/deserialize.h>
#include <ifm3d/deserialize/struct_tof_info_v4.hpp>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <ostream>
#include <thread>
#include <typeinfo>
// Namespace used for writing time "3s"
using namespace std::chrono_literals;
// Namespace used for json pointers
using namespace ifm3d::literals;

int main() {
  //////////////////////////
  // Create the O3R object
  //////////////////////////
  // Get the IP from the environment if defined
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  std::clog << "IP: " << IP << std::endl;

  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  // Get the current configuration of the camera in JSON format
  ifm3d::json conf = o3r->Get();

  //////////////////////////
  // Select the first available
  // 3D port from the configuration
  //////////////////////////
  uint16_t pcic_port = 0;
  std::string port_3d;

  for (const auto &port : o3r->Ports()) {
    if (port.type == "3D") {
      std::cout << "Using first available 3D port: " << port.port << std::endl;
      port_3d = port.port;
      pcic_port = port.pcic_port;
      break;
    }
  }

  /////////////////////////////////////////////////////////
  // Alternatively, manually pick the port corresponding
  // to your 2D camera (uncomment the line below and comment
  // the block above)
  /////////////////////////////////////////////////////////
  // std::string port_nb = "port0";
  // if (o3r->Port(port_nb).type != "3D") {
  //   std::cerr << "Please provide a 3D port number." << std::endl;
  //   return -1;
  // }
  // uint16_t pcic_port = o3r->Port(port_nb).pcic_port;
  // std::cout << "Using 3D port: " << port_nb << std::endl;

  //////////////////////////////////////////////////
  // Verify that a correct port number was provided
  // and create the framegrabber object
  //////////////////////////////////////////////////
  if (pcic_port == 0) {
    std::cerr << "No 3D port found in the configuration," << std::endl;
    return -1;
  }

  if (conf["ports"][port_3d]["state"] != "RUN") {
    std::cerr << "Port" << port_3d << "is in "
              << conf["ports"][port_3d]["state"]
              << " state. Please set the port state to RUN" << std::endl;
    return -1;
  }

  ////////////////////////////
  // Create the FrameGrabber object
  ////////////////////////////
  auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, pcic_port);

  // Define which buffer to retrieve and start the data stream
  fg->Start({ifm3d::buffer_id::TOF_INFO});

  //////////////////////////
  // Receive a frame:
  //////////////////////////
  auto future = fg->WaitForFrame();
  if (future.wait_for(std::chrono::milliseconds(1000)) !=
      std::future_status::ready) {
    std::cerr << "Timeout waiting for camera!" << std::endl;
    return -1;
  }
  auto frame = future.get();
  fg->Stop();

  //////////////////////////
  // Extract data from the buffer
  // Using the deserializer module
  //////////////////////////
  auto tof_info = ifm3d::TOFInfoV4::Deserialize(
      frame->GetBuffer(ifm3d::buffer_id::TOF_INFO));
  std::cout << "Sample of data available in the TOFInfoV4 buffer:" << std::endl;
  std::cout << "Current minimum measurement range:"
            << tof_info.measurement_range_min << "m" << std::endl;
  std::cout << "Current maximum measurement range:"
            << tof_info.measurement_range_max << "m" << std::endl;
  std::cout << "Temperature of the illumination module:"
            << tof_info.illu_temperature << "°C" << std::endl;

  return 0;
}
