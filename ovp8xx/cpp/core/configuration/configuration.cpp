/*
 * Copyright 2021-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

#include <fstream>
#include <ifm3d/device/o3r.h>
#include <iomanip>
#include <iostream>
#include <memory>
using namespace ifm3d::literals;

int main() {

  // Create the camera object
  auto o3r = std::make_shared<ifm3d::O3R>();

  // Get the current configuration of the camera in JSON format
  ifm3d::json conf = o3r->Get();

  // Display the current configuration
  std::cout << std::setw(4) << conf << std::endl;

  // Configure the device from a json string
  o3r->Set(ifm3d::json::parse(R"({"device":{"info":{"name": "my_new_o3r"}}})"));

  return 0;
}