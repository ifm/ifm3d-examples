/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
/* This example shows how to deserialize the
EXPOSURE_TIME, EXTRINSIC_CALIB, INTRINSIC_CALIB,
INVERSE_INTRINSIC_CALIBRATION and ILLUMINATION_TEMP
buffers to extract data. This example is only relevant
for the O3D3xx devices.*/
#include <chrono>
#include <cstdint>
#include <ifm3d/deserialize.h>
#include <ifm3d/deserialize/deserialize_o3d_buffers.hpp>
#include <ifm3d/device/o3d.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <string>
#include <thread>

using namespace std::chrono_literals;

int main() {
  // Get the IP from the environment if defined
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  std::clog << "IP: " << IP << std::endl;

  //////////////////////////
  // Declare the objects
  //////////////////////////
  // Declare the device object
  auto o3d = std::make_shared<ifm3d::O3D>(IP);

  ///////////////////////////////
  // Get a frame. Make sure
  // the device is in continuous
  // mode
  ///////////////////////////////
  auto fg = std::make_shared<ifm3d::FrameGrabber>(o3d);
  fg->Start({ifm3d::buffer_id::EXPOSURE_TIME, ifm3d::buffer_id::EXTRINSIC_CALIB,
             ifm3d::buffer_id::INTRINSIC_CALIB,
             ifm3d::buffer_id::INVERSE_INTRINSIC_CALIBRATION,
             ifm3d::buffer_id::ILLUMINATION_TEMP});
  std::this_thread::sleep_for(1s); // Grace period after starting the data
                                   // stream

  auto future = fg->WaitForFrame();
  if (future.wait_for(3s) != std::future_status::ready) {
    std::cerr << "Timeout waiting for camera!" << std::endl;
    return -1;
  }
  auto frame = future.get();

  ///////////////////////////////////
  // Extract the data from the frame
  // and deserialize it into usable
  // chunks.
  ///////////////////////////////////
  auto exposure_time_buffer = frame->GetBuffer(ifm3d::buffer_id::EXPOSURE_TIME);
  auto exposure_time =
      ifm3d::O3DExposureTimes::Deserialize(exposure_time_buffer);

  auto extrinsic_calib_buffer =
      frame->GetBuffer(ifm3d::buffer_id::EXTRINSIC_CALIB);
  auto extrinsic_calib =
      ifm3d::O3DExtrinsicCalibration::Deserialize(extrinsic_calib_buffer);

  auto intrinsic_calib_buffer =
      frame->GetBuffer(ifm3d::buffer_id::INTRINSIC_CALIB);
  auto intrinsic_calib =
      ifm3d::O3DInstrinsicCalibration::Deserialize(intrinsic_calib_buffer);

  auto inv_intrinsic_calib_buffer =
      frame->GetBuffer(ifm3d::buffer_id::INVERSE_INTRINSIC_CALIBRATION);
  auto inv_intrinsic_calib =
      ifm3d::O3DInverseInstrinsicCalibration::Deserialize(
          inv_intrinsic_calib_buffer);

  auto illu_temp_buffer = frame->GetBuffer(ifm3d::buffer_id::ILLUMINATION_TEMP);
  auto illu_temp = ifm3d::O3DILLUTemperature::Deserialize(illu_temp_buffer);

  ////////////////////////////////
  // Display a sample of the data
  ////////////////////////////////
  std::cout << "Exposure times (ms): " << std::endl;
  for (int i = 0; i < exposure_time.data.size(); i++) {
    std::cout << exposure_time.data[i] << std::endl;
  }

  std::cout << "Extrinsic calibration: " << std::endl;
  std::cout << "  Translations: " << extrinsic_calib.data[0] << ", "
            << extrinsic_calib.data[1] << ", " << extrinsic_calib.data[2]
            << std::endl;
  std::cout << "  Rotations: " << extrinsic_calib.data[3] << ", "
            << extrinsic_calib.data[4] << ", " << extrinsic_calib.data[5]
            << std::endl;

  std::cout << "Intrinsic calibration: " << std::endl;
  for (int i = 0; i < intrinsic_calib.data.size(); i++) {
    std::cout << intrinsic_calib.data[i] << std::endl;
  }
  std::cout << "Inverse intrinsic calibration: " << std::endl;
  for (int i = 0; i < inv_intrinsic_calib.data.size(); i++) {
    std::cout << inv_intrinsic_calib.data[i] << std::endl;
  }

  std::cout << "Illumination temperature: " << std::endl;
  for (int i = 0; i < illu_temp.data.size(); i++) {
    std::cout << illu_temp.data[i] << std::endl;
  }
  return 0;
}
