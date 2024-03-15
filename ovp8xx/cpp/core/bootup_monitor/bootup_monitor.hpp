/*
 * Copyright 2022-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <chrono>
#include <cstring>
#include <ifm3d/device/err.h>
#include <ifm3d/device/o3r.h>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>
using namespace std::chrono_literals;
using namespace ifm3d::literals;

class BootupMonitor {
public:
  static std::tuple<bool, std::string> MonitorVPUBootup(ifm3d::O3R::Ptr o3r, int timeout = 25, int wait_time = 1) {
    BootupMonitor monitor(o3r, timeout, wait_time);
    try {
      bool success = monitor.Monitor();
      return std::make_tuple(success, "");
    } catch (const std::runtime_error& e) {
      return std::make_tuple(false, e.what());
    }
  }

private:
  ifm3d::O3R::Ptr o3r_;
  const int timeout_; // in seconds
  const int wait_time_; // in seconds

  BootupMonitor(ifm3d::O3R::Ptr o3r, int timeout = 25, int wait_time = 1)
      : o3r_(o3r), timeout_(timeout), wait_time_(wait_time) {}

  bool Monitor(){
    std::clog << "Monitoring bootup sequence: ready to connect." << std::endl;
    auto start = std::chrono::steady_clock::now();
    ifm3d::json config;
    do {
      try {
        config = o3r_->Get();
        std::clog << "Connected." << std::endl;
      } catch (ifm3d::Error &e) {
        std::clog << "Awaiting data from VPU..." << std::endl;
      }
      if (!config.empty()) {
        std::clog << "Checking the init stages." << std::endl;
        auto conf_init_stages =
            config["/device/diagnostic/confInitStages"_json_pointer];
        std::clog << conf_init_stages << std::endl;
        for (auto it : conf_init_stages) {
          if (it == "applications") {
            std::clog << "Applications recognized" << std::endl
                      << "VPU fully booted." << std::endl;
            RetrieveBootDiagnostic();
            return true;
          }
          if (it == "ports") {
            std::clog << "Ports recognized." << std::endl;
          } else if (it == "device") {
            std::clog << "Device recognized." << std::endl;
          }
        }
      }
      std::this_thread::sleep_for(std::chrono::seconds(wait_time_));

    } while (std::chrono::steady_clock::now() - start <
             std::chrono::seconds(timeout_));
    throw std::runtime_error("VPU bootup sequence timed out, or connection failed.");
  }
  void RetrieveBootDiagnostic() {
    auto active_diag = o3r_->GetDiagnosticFiltered(
        ifm3d::json::parse(R"({"state": "active"})"))["/events"_json_pointer];
    for (auto error = active_diag.begin(); error != active_diag.end();
         ++error) {
      std::clog << "\n//////////////////////////////////" << std::endl;
      std::clog << *error << std::endl;
    }
  }
};