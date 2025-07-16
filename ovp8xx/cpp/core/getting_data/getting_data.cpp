/*
 * Copyright 2021-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <chrono>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>

using namespace std::chrono_literals;
using namespace ifm3d::literals;

int main() {

  //////////////////////////
  // Declare the objects
  //////////////////////////
  // Declare the device object (one object only, corresponding to the VPU)
  auto o3r = std::make_shared<ifm3d::O3R>();

  //////////////////////////
  // Select the first available
  // 3D port from the configuration
  //////////////////////////
  uint16_t pcic_port = 0;
  for (const auto &port : o3r->Ports()) {
    if (port.type == "3D") {
      std::cout << "Using first available 3D port: " << port.port << std::endl;
      pcic_port = port.pcic_port;
      break;
    }
  }

  /////////////////////////////////////////////////////////
  // Alternatively, manually pick the port corresponding
  // to your 3D camera (uncomment the line below and comment
  // the block above)
  /////////////////////////////////////////////////////////
  // std::string port_nb = "port2";
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

  auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, pcic_port);

  //////////////////////////
  // Start the framegrabber
  // and run the callback
  //////////////////////////

  // Set Schema and start the grabber
  fg->Start({ifm3d::buffer_id::NORM_AMPLITUDE_IMAGE,
             ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE, ifm3d::buffer_id::XYZ});

  //////////////////////////
  // Get a frame:
  //////////////////////////
  auto future = fg->WaitForFrame();
  if (future.wait_for(3s) != std::future_status::ready) {
    std::cerr << "Timeout waiting for camera!" << std::endl;
    return -1;
  }
  auto frame = future.get();

  //////////////////////////
  // Example for 3D data:
  //////////////////////////
  auto dist = frame->GetBuffer(ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE);

  std::cout << dist.height() << " " << dist.width() << std::endl;

  fg->Stop();
  return 0;
}
