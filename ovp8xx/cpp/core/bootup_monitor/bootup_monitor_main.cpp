/*
 * Copyright 2022-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <ifm3d/device/o3r.h>

#include "bootup_monitor.hpp"

int main() {
  const char *IP = std::getenv("IFM3D_IP");
  if (!IP) {
    IP = ifm3d::DEFAULT_IP.c_str();
    std::clog << "Using default IP" << std::endl;
  }
  std::clog << "IP: " << IP << std::endl;

  auto o3r = std::make_shared<ifm3d::O3R>(IP);
  
  if(auto err = BootupMonitor::MonitorVPUBootup(o3r, std::chrono::seconds(25s).count()); !std::get<bool>(err))
  {
    // Error handling
    std::cout << "Error: " << std::get<1>(err) << std::endl;
  }

  return 0;
}