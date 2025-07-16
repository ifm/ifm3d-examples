/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

//
// ex-getmac.cpp
//
// Request the MAC address from the camera. The MAC address can be used as
// a unique identifier.
//

#include <ifm3d/device/device.h>
#include <iostream>

int main(int argc, const char **argv) {
  // get access to the camera
  auto cam = ifm3d::Device::MakeShared();

  // get the JSON configuration data from the camera
  auto jsonConfig = cam->ToJSON();

  // print out the MAC address
  std::cout << "The MAC address of the camera: "
            << jsonConfig["ifm3d"]["Net"]["MACAddress"] << std::endl;

  return 0;
}
