/*
 * Copyright 2025-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

// Legacy IMU data example with manual deserialization for ifm3d < 1.6.15.
// If you are using ifm3d >= 1.6.15, please use imu_data.cpp instead,
// which uses the built-in IMUInfoV1 deserializer.

#include <atomic>
#include <chrono>
#include <cstring>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <memory>
#include <thread>
#include <vector>

using namespace std::chrono_literals;
using namespace ifm3d::literals;

// IMU data structures based on the Python deserializer
struct IMUSample {
  uint16_t hw_timestamp;
  uint64_t timestamp;
  float temperature;
  float accel_x, accel_y, accel_z;
  float gyro_x, gyro_y, gyro_z;

  static constexpr size_t size() {
    return 2 + 8 + 4 * 7; // 2 + 8 + 28 = 38 bytes
  }
};

struct ExtrinsicData {
  float rot_x, rot_y, rot_z;
  float trans_x, trans_y, trans_z;

  static constexpr size_t size() {
    return 6 * 4; // 24 bytes
  }
};

struct IMUOutput {
  uint32_t imu_version;
  uint32_t num_samples;
  std::vector<IMUSample> imu_samples;
  ExtrinsicData extrinsic_imu_to_user;
  ExtrinsicData extrinsic_imu_to_vpu;
  uint64_t imu_fifo_rcv_timestamp;
};

// IMU data deserializer
class IMUDeserializer {
public:
  static IMUOutput parse(const std::vector<uint8_t> &data) {
    IMUOutput result;
    size_t offset = 0;

    // Parse IMU version (start directly like Python version)
    if (offset + 4 > data.size())
      throw std::runtime_error("Data truncated");
    std::memcpy(&result.imu_version, &data[offset], 4);
    offset += 4;

    // Parse IMU samples (DEFAULT_IMU_SAMPLES = 128 like Python)
    const uint32_t DEFAULT_IMU_SAMPLES = 128;
    result.imu_samples.reserve(DEFAULT_IMU_SAMPLES);
    for (uint32_t i = 0; i < DEFAULT_IMU_SAMPLES; ++i) {
      if (offset + IMUSample::size() > data.size()) {
        throw std::runtime_error("Data truncated while reading samples");
      }

      IMUSample sample;
      std::memcpy(&sample.hw_timestamp, &data[offset], 2);
      offset += 2;
      std::memcpy(&sample.timestamp, &data[offset], 8);
      offset += 8;
      std::memcpy(&sample.temperature, &data[offset], 4);
      offset += 4;
      std::memcpy(&sample.accel_x, &data[offset], 4);
      offset += 4;
      std::memcpy(&sample.accel_y, &data[offset], 4);
      offset += 4;
      std::memcpy(&sample.accel_z, &data[offset], 4);
      offset += 4;
      std::memcpy(&sample.gyro_x, &data[offset], 4);
      offset += 4;
      std::memcpy(&sample.gyro_y, &data[offset], 4);
      offset += 4;
      std::memcpy(&sample.gyro_z, &data[offset], 4);
      offset += 4;

      result.imu_samples.push_back(sample);
    }

    // Parse number of samples (after all samples, like Python)
    if (offset + 4 > data.size())
      throw std::runtime_error("Data truncated");
    std::memcpy(&result.num_samples, &data[offset], 4);
    offset += 4;
    // Parse extrinsic IMU to user
    if (offset + ExtrinsicData::size() > data.size()) {
      throw std::runtime_error("Data truncated while reading extrinsic data");
    }
    std::memcpy(&result.extrinsic_imu_to_user.trans_x, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_user.trans_y, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_user.trans_z, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_user.rot_x, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_user.rot_y, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_user.rot_z, &data[offset], 4);
    offset += 4;

    // Parse extrinsic IMU to VPU
    if (offset + ExtrinsicData::size() > data.size()) {
      throw std::runtime_error("Data truncated while reading extrinsic data");
    }
    std::memcpy(&result.extrinsic_imu_to_vpu.trans_x, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_vpu.trans_y, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_vpu.trans_z, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_vpu.rot_x, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_vpu.rot_y, &data[offset], 4);
    offset += 4;
    std::memcpy(&result.extrinsic_imu_to_vpu.rot_z, &data[offset], 4);
    offset += 4;

    // Parse receive timestamp
    if (offset + 8 > data.size()) {
      throw std::runtime_error("Data truncated while reading timestamp");
    }
    std::memcpy(&result.imu_fifo_rcv_timestamp, &data[offset], 8);
    offset += 8;

    return result;
  }
};

// Function to print IMU data
void print_imu_data(const IMUOutput &imu_data) {
  std::cout << "IMU version: " << imu_data.imu_version << std::endl;
  std::cout << "Number of Samples: " << imu_data.num_samples << std::endl;

  if (!imu_data.imu_samples.empty()) {
    const auto &first_sample = imu_data.imu_samples[0];
    std::cout << "First sample:" << std::endl;
    std::cout << "    Hardware timestamp: " << first_sample.hw_timestamp
              << std::endl;
    std::cout << "    Acquisition timestamp: " << first_sample.timestamp
              << std::endl;
    std::cout << "    Temperature: " << first_sample.temperature << std::endl;
    std::cout << "    Acceleration [m/s²]:" << std::endl;
    std::cout << "        x: " << first_sample.accel_x << std::endl;
    std::cout << "        y: " << first_sample.accel_y << std::endl;
    std::cout << "        z: " << first_sample.accel_z << std::endl;
    std::cout << "    Angular rate [rad/s]:" << std::endl;
    std::cout << "        x: " << first_sample.gyro_x << std::endl;
    std::cout << "        y: " << first_sample.gyro_y << std::endl;
    std::cout << "        z: " << first_sample.gyro_z << std::endl;
  }

  std::cout << "Extrinsic IMU to User:" << std::endl;
  std::cout << "    rot_x: " << imu_data.extrinsic_imu_to_user.rot_x
            << std::endl;
  std::cout << "    rot_y: " << imu_data.extrinsic_imu_to_user.rot_y
            << std::endl;
  std::cout << "    rot_z: " << imu_data.extrinsic_imu_to_user.rot_z
            << std::endl;
  std::cout << "    trans_x: " << imu_data.extrinsic_imu_to_user.trans_x
            << std::endl;
  std::cout << "    trans_y: " << imu_data.extrinsic_imu_to_user.trans_y
            << std::endl;
  std::cout << "    trans_z: " << imu_data.extrinsic_imu_to_user.trans_z
            << std::endl;

  std::cout << "Extrinsic IMU to VPU:" << std::endl;
  std::cout << "    rot_x: " << imu_data.extrinsic_imu_to_vpu.rot_x
            << std::endl;
  std::cout << "    rot_y: " << imu_data.extrinsic_imu_to_vpu.rot_y
            << std::endl;
  std::cout << "    rot_z: " << imu_data.extrinsic_imu_to_vpu.rot_z
            << std::endl;
  std::cout << "    trans_x: " << imu_data.extrinsic_imu_to_vpu.trans_x
            << std::endl;
  std::cout << "    trans_y: " << imu_data.extrinsic_imu_to_vpu.trans_y
            << std::endl;
  std::cout << "    trans_z: " << imu_data.extrinsic_imu_to_vpu.trans_z
            << std::endl;

  std::cout << "Receive Timestamp: " << imu_data.imu_fifo_rcv_timestamp
            << std::endl;
}

// Global variable to count processed frames
std::atomic<int> frame_count{0};
const int MAX_FRAMES = 5;

// Callback function for processing IMU frames
void imu_callback(ifm3d::Frame::Ptr frame) {
  if (frame_count >= MAX_FRAMES) {
    return; // Stop processing after MAX_FRAMES
  }

  frame_count++;
  std::cout << "\n=== Frame " << frame_count << " ===" << std::endl;

  try {
    // Check if the frame is valid before processing
    if (!frame) {
      std::cerr << "Received invalid frame, skipping..." << std::endl;
      return;
    }

    auto imu_buffer = frame->GetBuffer(ifm3d::buffer_id::O3R_RESULT_IMU);

    // Check buffer validity
    if (imu_buffer.width() == 0 || imu_buffer.height() == 0) {
      std::cerr << "Empty IMU buffer received, skipping..." << std::endl;
      return;
    }

    // Convert buffer to vector<uint8_t> for deserializer
    auto *buffer_data = imu_buffer.ptr<uint8_t>(0);
    size_t buffer_size = imu_buffer.width() * imu_buffer.height();

    std::vector<uint8_t> imu_data_raw(buffer_data, buffer_data + buffer_size);

    // Deserialize and print IMU data
    try {
      auto imu_data = IMUDeserializer::parse(imu_data_raw);
      print_imu_data(imu_data);
    } catch (const std::exception &e) {
      std::cerr << "Error deserializing IMU data: " << e.what() << std::endl;
    }

  } catch (const std::exception &e) {
    std::cerr << "Error in callback: " << e.what() << std::endl;
  }
}

int main() {
  //////////////////////////
  // Declare the objects
  //////////////////////////
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  std::cout << "IP: " << IP << std::endl;

  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  //////////////////////////
  // Configure IMU port
  //////////////////////////
  std::string port_imu = "port6";
  auto port_info = o3r->Port(port_imu);

  if (port_info.type.empty()) {
    std::cerr << "Port " << port_imu << " not found or not configured for IMU"
              << std::endl;
    std::cerr << "Please configure an IMU port first" << std::endl;
    return -1;
  }

  uint16_t pcic_port = port_info.pcic_port;
  std::cout << "Using IMU port: " << port_imu << std::endl;

  //////////////////////////
  // Check port state and set to RUN if needed
  //////////////////////////
  auto config = o3r->Get({"/ports/port6/state"});
  std::string current_state = config["ports"][port_imu]["state"];

  if (current_state != "RUN") {
    std::cout << "Changing port state from " << current_state << " to RUN"
              << std::endl;
    o3r->Set({{"ports", {{port_imu, {{"state", "RUN"}}}}}});
    std::this_thread::sleep_for(1s); // Wait for state change
  }

  //////////////////////////
  // Create framegrabber and start with callback
  //////////////////////////
  auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, pcic_port);

  // Start the framegrabber with empty buffer list (like Python version)
  fg->Start({});

  std::cout << "Framegrabber started, waiting for IMU data to stabilize..."
            << std::endl;
  std::this_thread::sleep_for(2s); // Wait for IMU data to stabilize

  // Register callback function
  fg->OnNewFrame(&imu_callback);

  std::cout << "Collecting " << MAX_FRAMES << " frames..." << std::endl;

  // Wait for callback to process the desired number of frames
  while (frame_count < MAX_FRAMES) {
    std::this_thread::sleep_for(500ms);
  }

  //////////////////////////
  // Cleanup
  //////////////////////////
  fg->Stop();
  std::cout << "\nIMU data collection completed." << std::endl;

  return 0;
}
