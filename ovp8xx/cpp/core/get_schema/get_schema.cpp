/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
// This example shows how to get the JSON schema
// corresponding to the current configuration of
// the device.
// The schema can be used to validate the configuration
// and provides details like data type, default, min, and max values for
// each parameter.
#include <chrono>
#include <ifm3d/device/o3r.h>
#include <iostream>
#include <iterator>
#include <memory>

using namespace ifm3d::literals;

int main() {
  // Getting the IP address from the environment variable or
  // using the default IP address if not defined.
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  auto schema = o3r->GetSchema();

  std::cout << "Displaying a sample of the JSON schema." << std::endl;
  std::cout << "Schema for the network and fieldbus interfaces:" << std::endl;
  std::cout << schema["properties"]["device"]["properties"]["network"]
                     ["properties"]["interfaces"]
                         .dump(2)
            << std::endl;

  return 0;
}
