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
  std::string ports_string = "/ports";
  ifm3d::json::json_pointer ports_ptr(ports_string);
  ifm3d::json ports_conf = o3r->Get({ports_string})[ports_ptr];

  std::string port_nb;
  for (const auto &port : ports_conf.items()) {
    ifm3d::json::json_pointer type_ptr("/" + port.key() +
                                       "/info/features/type");
    if (ports_conf[type_ptr] == "3D") {
      port_nb = port.key();
      std::cout << "Using first available 3D port: " << port_nb << std::endl;
      break;
    }
  }

  /////////////////////////////////////////////////////////
  // Alternatively, manually pick the port corresponding
  // to your 3D camera (uncomment the line below and comment
  // the block above)
  /////////////////////////////////////////////////////////
  // std::string port_nb = "port0";

  // Verify that a correct port number was provided
  if (port_nb.empty()) {
    std::cerr << "No 3D port found in the configuration," << std::endl;
    std::cerr
        << "Either connect a 3D camera or manually provide the port number."
        << std::endl;
    return -1;
  }
  ///////////////////////////////////////////////////////
  // Get the PCIC port number for the selected port
  // and create the FrameGrabber
  /////////////////////////////////////////////////////////
  std::string pcic_port_string = "/ports/" + port_nb + "/data/pcicTCPPort";
  ifm3d::json::json_pointer pcic_port_ptr(pcic_port_string);
  const auto pcic_port = o3r->Get({pcic_port_string})[pcic_port_ptr];
  auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, pcic_port);

  //////////////////////////
  // Start the framegrabber
  // and run the callback
  //////////////////////////

  // Set Schema and start the grabber
  fg->Start({ifm3d::buffer_id::AMPLITUDE_IMAGE,
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