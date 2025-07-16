/*
 * Copyright 2021-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <chrono>
#include <ifm3d/common/json_impl.hpp>
#include <ifm3d/device/err.h>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <string>
#include <thread>

using namespace std::chrono_literals;
using namespace ifm3d::literals;

void Callback(ifm3d::Frame::Ptr frame) {
  auto dist = frame->GetBuffer(ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE);
  std::cout << "Distance image dimensions:" << std::endl;
  std::cout << dist.height() << " " << dist.width() << std::endl;
}

int main() {
  // Get the IP from the environment if defined
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  std::clog << "IP: " << IP << std::endl;

  //////////////////////////
  // Declare the objects
  //////////////////////////
  // Declare the device object (one object only, corresponding to the VPU)
  auto o3r = std::make_shared<ifm3d::O3R>(IP);

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
  // and register the callback
  //////////////////////////

  // Set Schema and start the grabber
  fg->Start({ifm3d::buffer_id::NORM_AMPLITUDE_IMAGE,
             ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE, ifm3d::buffer_id::XYZ});

  // Register callback function
  fg->OnNewFrame(&Callback);

  // This sleep is to prevent the program from before the
  // callback has time to execute.
  std::this_thread::sleep_for(1s);
  fg->Stop();

  return 0;
}
