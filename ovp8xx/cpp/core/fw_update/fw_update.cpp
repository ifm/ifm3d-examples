/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
// This example shows how to update the firmware
// of an O3R device.

#include <filesystem>
#include <ifm3d/device/o3r.h>
#include <ifm3d/swupdater/swupdater.h>
#include <iostream>

using namespace ifm3d::literals;

int main() {
  // Provide the path to the sofware update file:
  std::filesystem::path FILENAME =
      "/path/to/o3r/fw/OVP81x_Firmware_1.10.13.5502.swu";
  if (std::filesystem::exists(FILENAME)) {
    std::cout << "File exists: " << FILENAME << std::endl;
  } else {
    std::cerr << "File does not exist: " << FILENAME << std::endl;
  }

  // Getting the IP address from the environment variable or
  // using the default IP address if not defined.
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  auto o3r = std::make_shared<ifm3d::O3R>(IP);
  auto swu = std::make_shared<ifm3d::SWUpdater>(o3r);

  // Reboot the system to recovery mode
  std::cout << "Rebooting to recovery mode..." << std::endl;
  swu->RebootToRecovery();
  swu->WaitForRecovery();

  // Flash the firmware
  std::cout << "Flashing firmware..." << std::endl;
  if (swu->FlashFirmware(FILENAME, 1800)) {
    swu->WaitForProductive();
    std::cout << "Firmware update successful. System ready!" << std::endl;
  } else {
    std::cerr << "Firmware update failed." << std::endl;
  }

  // Check the version after update
  std::cout << "Current version: " << o3r->Get({"/device/swVersion/firmware"})
            << std::endl;

  return 0;
}
