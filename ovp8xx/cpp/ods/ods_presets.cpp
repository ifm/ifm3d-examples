/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <iomanip>
#include <iostream>
#include <fstream>
#include <memory>
#include <thread>
#include <ifm3d/device/o3r.h>
using namespace ifm3d::literals;
using namespace std::chrono_literals;


int main() {
  // Get the IP from the environment if defined
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP") : ifm3d::DEFAULT_IP.c_str();
  std::clog << "IP: " << IP << std::endl;

  // Create the camera object
  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  ////////////////////////////////////
  // Path to the configuration files
  // Note that the configuration files will be
  // copied to the build folder.
  ////////////////////////////////////
  std::string config_extrinsic_path = "./configs/extrinsic_two_heads.json";
  std::string config_presets_path = "./configs/ods_two_heads_presets.json";

  ///////////////////////////////////////////
  // Configuring the device (application and
  // extrinsic calibration)
  ///////////////////////////////////////////
  std::ifstream config_extrinsic_file;
  config_extrinsic_file.exceptions(std::ifstream::failbit | std::ifstream::badbit);
  std::stringstream config_extrinsic_buffer;
  try {
      config_extrinsic_file.open(config_extrinsic_path);
      if (config_extrinsic_file.is_open()) {
      config_extrinsic_buffer << config_extrinsic_file.rdbuf();
      }
      o3r->Set(ifm3d::json::parse(config_extrinsic_buffer.str()));
    } catch (const std::ifstream::failure &e) {
      std::cerr << "Caught exception while reading extrinsic configuration file: "
                << e.what() << std::endl;
    } catch (...) {
      std::cerr << "Unknown error while reading configuration file."
                << std::endl;
    }

  std::ifstream config_presets_file;
  config_presets_file.exceptions(std::ifstream::failbit | std::ifstream::badbit);
  std::stringstream config_presets_buffer;
  try {
      config_presets_file.open(config_presets_path);
      if (config_presets_file.is_open()) {
      config_presets_buffer << config_presets_file.rdbuf();
      }
      o3r->Set(ifm3d::json::parse(config_presets_buffer.str()));
    } catch (const std::ifstream::failure &e) {
      std::cerr << "Caught exception while reading presets configuration file: "
                << e.what() << std::endl;
    } catch (...) {
      std::cerr << "Unknown error while reading configuration file."
                << std::endl;
    }

  /////////////////////////////////////////////
  // Set the application to RUN state (assuming app0)
  // and check the currently running preset (if any)
  /////////////////////////////////////////////
  o3r->Set((ifm3d::json::parse(R"({"applications":{"instances":{"app0": {"state": "RUN"}}}})")));

  std::cout << "Currently running preset:" << std::endl;
  std::string j_string = "/applications/instances/app0/presets/load";
  ifm3d::json::json_pointer j(j_string);
  auto config = o3r->Get({j_string})[j];
  std::cout<< config << std::endl;

  /////////////////////////////////////////////
  // Switch to a different preset
  /////////////////////////////////////////////
  std::this_thread::sleep_for(5s);
  std::cout<< "Switching to preset idx 2" << std::endl;
  int preset_idx = 2;
  std::string new_config = R"({"applications":{"instances":{"app0":{"presets":{"load":{"identifier":)" + std::to_string(preset_idx) + R"(}, "command": "load"}}}}})";
  o3r->Set(ifm3d::json::parse(new_config));

  std::cout << "Currently running preset:" << std::endl;
  j_string = "/applications/instances/app0/presets/load";
  j = ifm3d::json::json_pointer(j_string);
  config = o3r->Get({j_string})[j];
  std::cout<< config << std::endl;

  return 0;
} 