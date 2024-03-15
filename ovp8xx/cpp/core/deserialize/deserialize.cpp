/*
 * Copyright 2021-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <chrono>
#include <ifm3d/deserialize.h>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <thread>
// Namespace used for writing time "3s"
using namespace std::chrono_literals;
// Namespace used for json pointers
using namespace ifm3d::literals;

int main() {
  //////////////////////////
  // Create the O3R object
  //////////////////////////
  // Get the IP from the environment if defined
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP") : ifm3d::DEFAULT_IP.c_str();
  std::clog << "IP: " << IP << std::endl;

  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  //////////////////////////
  // Select the first available
  // 2D port from the configuration
  //////////////////////////
  uint16_t pcic_port = 0;
  for (const auto &port : o3r->Ports()) {
    if (port.type == "2D") {
      std::cout << "Using first available 3D port: " << port.port << std::endl;
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
  // if (o3r->Port(port_nb).type != "2D") {
  //   std::cerr << "Please provide a 2D port number." << std::endl;
  //   return -1;
  // }
  // uint16_t pcic_port = o3r->Port(port_nb).pcic_port;
  // std::cout << "Using 2D port: " << port_nb << std::endl;

  //////////////////////////////////////////////////
  // Verify that a correct port number was provided
  // and create the framegrabber object
  //////////////////////////////////////////////////
  if (pcic_port == 0) {
    std::cerr << "No 2D port found in the configuration," << std::endl;
    return -1;
  }

  ////////////////////////////
  // Create the FrameGrabber object
  ////////////////////////////
  auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, pcic_port);

  // Define which buffer to retrieve and start the data stream
  fg->Start({ifm3d::buffer_id::RGB_INFO});

  //////////////////////////
  // Receive a frame:
  //////////////////////////
  auto future = fg->WaitForFrame();
  if (future.wait_for(3s) != std::future_status::ready) {
    std::cerr << "Timeout waiting for camera!" << std::endl;
    return -1;
  }
  auto frame = future.get();
  // Get the data from the relevant buffer
  auto rgb_info_buffer = frame->GetBuffer(ifm3d::buffer_id::RGB_INFO);
  fg->Stop();

  //////////////////////////
  // Extract data from the buffer
  // Using the deserializer module
  //////////////////////////
  auto rgb_info = ifm3d::RGBInfoV1::Deserialize(rgb_info_buffer);
  std::cout << "Sample of data available in the RGBInfoV1 buffer:" << std::endl;
  std::cout << "RGB info timestamp: " << rgb_info.timestamp_ns << std::endl;
  std::cout << "Exposure time: " << rgb_info.exposure_time << std::endl;
  std::cout << "Intrinsic calibration model id: "
            << rgb_info.intrinsic_calibration.model_id << std::endl;
  std::cout << "Intrinsic calibration parameter [0]: "
            << rgb_info.intrinsic_calibration.model_parameters[0] << std::endl;
  return 0;
}