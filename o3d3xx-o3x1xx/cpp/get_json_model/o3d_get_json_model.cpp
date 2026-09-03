/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
//
// ex-get_json_model.cpp
//
// Capture a frame from the camera, to retrive the JOSN_MODEL.
//

#include <iostream>
#include <memory>
#include <string.h>

#include <ifm3d/device/device.h>
#include <ifm3d/fg.h>

int main(int argc, const char **argv) {
  auto cam = ifm3d::Device::MakeShared();

  ifm3d::FrameGrabber::Ptr fg = std::make_shared<ifm3d::FrameGrabber>(cam);

  fg->Start({ifm3d::buffer_id::JSON_MODEL});

  auto frame = fg->WaitForFrame();

  if (frame.wait_for(std::chrono::milliseconds(1000)) !=
      std::future_status::ready) {
    std::cerr << "Timeout waiting for camera!" << std::endl;
    return -1;
  }

  auto json_model = frame.get()->GetBuffer(ifm3d::buffer_id::JSON_MODEL);

  std::string json =
      std::string(json_model.ptr<char>(0),
                  strnlen(json_model.ptr<char>(0), json_model.size()));
  std::cout << "JSON MODEL : \n" << json << std::endl;

  return 0;
}
