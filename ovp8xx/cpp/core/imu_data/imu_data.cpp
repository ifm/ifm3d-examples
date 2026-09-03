/*
 * Copyright 2025-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

// The IMUInfoV1 is available from ifm3d >= 1.6.15 and firmware version 1.4.30
// or higher. For older ifm3d versions, please  refer to imu_data_legacy.cpp

#include <chrono>
#include <ifm3d/deserialize.h>
#include <ifm3d/deserialize/struct_imu_info_v1.hpp>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>

using namespace std::chrono_literals;

int main() {
  const std::string ip = "192.168.0.69";
  const std::string port_imu = "port6";

  std::shared_ptr<ifm3d::FrameGrabber> fg;

  try {
    auto o3r = std::make_shared<ifm3d::O3R>(ip);
    auto port_info = o3r->Port(port_imu);

    if (port_info.type.empty()) {
      std::cerr << "Port " << port_imu << " not found or not configured for IMU"
                << std::endl;
      std::cerr << "Please configure an IMU port first" << std::endl;
      return -1;
    }

    const uint16_t pcic_port = port_info.pcic_port;
    fg = std::make_shared<ifm3d::FrameGrabber>(o3r, pcic_port);

    auto config = o3r->Get({"/ports/port6/state"});
    const std::string current_state = config["ports"]["port6"]["state"];

    if (current_state != "RUN") {
      std::cout << "Change the port state from " << current_state << " to RUN"
                << std::endl;
      o3r->Set({{"ports", {{"port6", {{"state", "RUN"}}}}}});
      std::this_thread::sleep_for(1s);
    }

    fg->Start({ifm3d::buffer_id::O3R_RESULT_IMU});

    auto future = fg->WaitForFrame();
    if (future.wait_for(500ms) != std::future_status::ready) {
      throw std::runtime_error(
          "Failed to receive IMU frame within the timeout period.");
    }

    auto frame = future.get();
    auto imu_data = ifm3d::IMUInfoV1::Deserialize(
        frame->GetBuffer(ifm3d::buffer_id::O3R_RESULT_IMU));

    std::cout << "IMU version: " << imu_data.imu_version << "\n" << std::endl;
    std::cout << "Number of Samples: " << imu_data.num_samples << "\n"
              << std::endl;
    std::cout << "Receive Timestamp: " << imu_data.imu_fifo_rcv_timestamp
              << "\n"
              << std::endl;
    std::cout << "Extrinsic IMU to User: \n"
              << "            rot_x: " << imu_data.extrinsic_imu_to_user.rot_x
              << "\n"
              << "            rot_y: " << imu_data.extrinsic_imu_to_user.rot_y
              << "\n"
              << "            rot_z: " << imu_data.extrinsic_imu_to_user.rot_z
              << "\n"
              << "            trans_x: "
              << imu_data.extrinsic_imu_to_user.trans_x << "\n"
              << "            trans_y: "
              << imu_data.extrinsic_imu_to_user.trans_y << "\n"
              << "            trans_z: "
              << imu_data.extrinsic_imu_to_user.trans_z << "\n"
              << std::endl;

    if (!imu_data.imu_samples.empty()) {
      auto sample = imu_data.imu_samples[0];
      std::cout << "First IMU Sample: \n"
                << "          HW Timestamp: " << sample.hw_timestamp << "\n"
                << "          Timestamp: " << sample.timestamp << "\n"
                << "          Temperature: " << sample.temperature << "\n"
                << "          Acceleration X: " << sample.acc_x << "\n"
                << "          Acceleration Y: " << sample.acc_y << "\n"
                << "          Acceleration Z: " << sample.acc_z << "\n"
                << "          Gyro X: " << sample.gyro_x << "\n"
                << "          Gyro Y: " << sample.gyro_y << "\n"
                << "          Gyro Z: " << sample.gyro_z << "\n"
                << std::endl;
    }

    fg->Stop();
    return 0;
  } catch (const std::exception &e) {
    if (fg) {
      fg->Stop();
    }
    std::cerr << "Error: " << e.what() << std::endl;
    return -1;
  }
}
