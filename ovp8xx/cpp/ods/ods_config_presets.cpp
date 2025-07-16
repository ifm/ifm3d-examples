// Copyright 2025-present ifm electronic, gmbh
// SPDX-License-Identifier: Apache-2.0
#include <chrono> // For std::chrono::seconds
#include <fstream>
#include <ifm3d/common/json.hpp>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread> // For std::this_thread::sleep_for
#include <tuple>  // For std::tuple

using ifm3d::json;

// Diagnostic callback function
void async_diagnostic_callback(const std::string &message,
                               const std::string &app_name) {
  using ifm3d::json;

  // Parse the diagnostic message
  json diagnostic = json::parse(message);

  // Extract groups and check the status of the specified application
  auto groups = diagnostic.value("groups", json::object());
  std::string app_status = groups.value(app_name, "unknown");

  std::cout << "\nNew Diagnostic: The status of application '" << app_name
            << "': " << app_status << std::endl;

  // Check if the application is in a critical state
  if (app_status == "critical") {
    std::cout << "⚠️ Application '" << app_name
              << "' is in a critical state! Stop the Robot!!" << std::endl;
  }
}

// Function to set configuration from a config file and get application name
inline std::tuple<json, std::string, std::string>
SetConfigAndGetAppName(std::shared_ptr<ifm3d::O3R> o3r,
                       const std::string &config_path) {
  // Open the file and parse the JSON
  std::ifstream file(config_path);
  if (!file) {
    throw std::runtime_error("Failed to open config file: " + config_path);
  }
  json config = json::parse(file);
  file.close();

  // Set the configuration on the device
  std::cout << "Setting configuration from file: " << config_path << std::endl;
  o3r->Set(config);

  // Retrieve the application instance and name
  auto instances = config["applications"]["instances"];
  if (instances.empty()) {
    throw std::runtime_error(
        "No applications found in the configuration file.");
  }
  std::string app_instance = instances.begin().key();
  std::string app_name = instances[app_instance]["name"];

  return {config, app_instance, app_name};
}

// Function to change the preset
void ChangePreset(std::shared_ptr<ifm3d::O3R> o3r, const std::string &app_name,
                  int preset_idx) {
  json preset_config = {{"applications",
                         {{"instances",
                           {{app_name,
                             {{"presets",
                               {{"load", {{"identifier", preset_idx}}},
                                {"command", "load"}}}}}}}}}};
  o3r->Set(preset_config);

  auto loaded_preset = o3r->Get(
      {"/applications/instances/" + app_name +
       "/configuration/zones/zoneConfigID"})["applications"]["instances"]
                                            [app_name]["configuration"]["zones"]
                                            ["zoneConfigID"];
  if (loaded_preset == preset_idx) {
    std::cout << "Preset " << preset_idx << " loaded successfully."
              << std::endl;
  } else {
    std::cout << "Failed to load preset " << preset_idx
              << ". Current preset: " << loaded_preset << std::endl;
  }
}

int main() {
  const std::string config_path = "../configs/ods_two_heads_presets.json";

  // Device specific configuration
  std::string IP = "192.168.0.69";
  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  // Reset applications
  std::cout << "Resetting applications..." << std::endl;
  o3r->Reset({"/applications"});

  // Set configuration and retrieve the application name
  json config_snippet;
  std::string app_instance, app_name;
  try {
    std::tie(config_snippet, app_instance, app_name) =
        SetConfigAndGetAppName(o3r, config_path);
  } catch (const std::exception &e) {
    std::cerr << "Error setting configuration or retrieving application name: "
              << e.what() << std::endl;
    return 1;
  }
  json run_state = {
      {"applications", {{"instances", {{app_instance, {{"state", "RUN"}}}}}}}};
  json conf_state = {
      {"applications", {{"instances", {{app_instance, {{"state", "CONF"}}}}}}}};
  // Set application state to RUN
  o3r->Set(run_state);

  // Check if the configuration was applied correctly
  try {
    std::string path = "/applications/instances/" + app_instance + "/name";
    auto app = o3r->Get({path});

    std::string expected_name =
        config_snippet["applications"]["instances"][app_instance]["name"];
    std::string actual_name =
        app["applications"]["instances"][app_instance]["name"];

    std::string status =
        (actual_name == expected_name) ? "✅ Match" : "❌ Mismatch";
    std::cout << "Checking application name: Expected '" << expected_name
              << "', Applied '" << actual_name << "' → " << status << std::endl;
  } catch (const std::exception &e) {
    std::cerr << "Error retrieving application state: " << e.what()
              << std::endl;
  }

  // Start diagnostic monitoring
  std::this_thread::sleep_for(std::chrono::seconds(2));
  auto diag_fg = std::make_shared<ifm3d::FrameGrabber>(o3r, 50009);
  diag_fg->OnAsyncError([app_instance](int id, const std::string &message) {
    async_diagnostic_callback(message, app_instance);
  });
  std::clog << "Starting async diagnostic monitoring. \nErrors ids and "
               "descriptions will be logged."
            << std::endl;
  diag_fg->Start({});

  // Change presets
  ChangePreset(o3r, app_instance, 1);

  // Add a 5-second delay
  std::this_thread::sleep_for(std::chrono::seconds(5));

  ChangePreset(o3r, app_instance, 2);
  json range_of_interest = {
      {"applications",
       {{"instances",
         {{app_instance,
           {{"configuration", {{"grid", {{"rangeOfInterest", 10.0}}}}}}}}}}}};

  // Attempt to change configuration while in RUN state (expected to fail)
  try {
    std::cout
        << "Trying to change a conf parameter while the app is in RUN state."
        << std::endl;
    std::cout << "This is expected to fail!" << std::endl;
    o3r->Set(range_of_interest);
  } catch (const std::exception &e) {
    std::cout << "Cannot set a CONF parameter while app is in RUN state: "
              << e.what() << std::endl;
  }

  // Attempt to change configuration while in CONF state
  try {
    std::cout
        << "Trying to change a CONF parameter while the app is in CONF state"
        << std::endl;
    o3r->Set(conf_state);
    o3r->Set(range_of_interest);
    o3r->Set(run_state);
    std::cout << "Configuration change successful!" << std::endl;
  } catch (const std::exception &e) {
    std::cout << "Error while changing a CONF parameter: " << e.what()
              << std::endl;
  }

  std::cout << "ODS configuration with presets completed!" << std::endl;
  return 0;
}
