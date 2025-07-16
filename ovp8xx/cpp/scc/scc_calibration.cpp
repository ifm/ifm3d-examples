/*
 * Copyright 2025-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
/* This example shows how to calibrate a camera
 * using the SCC application.
 * The calibration is triggered by sending the
 * "calibrate" commande in JSON with the Set function.
 * The result is received in the O3R_RESULT_JSON
 * buffer, through the previously registered callback.
 * The generated values can be written to the device
 * using the "writeToDevice" command, in JSON.
 */

#include <fstream>
#include <ifm3d/common/json.hpp>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <memory>

using namespace ifm3d::literals;
using namespace std::chrono_literals;
using ifm3d::json;

// Global variable to track calibration status
bool CALIBRATED = false;

// Function to send a command to the SCC application
void send_command(std::shared_ptr<ifm3d::O3R> o3r,
                  const std::string &app_instance, const std::string &command) {
  try {
    json command_config = {
        {"applications",
         {{"instances",
           {{app_instance, {{"configuration", {{"command", command}}}}}}}}}};
    o3r->Set(command_config);
    std::cout << "Command '" << command << "' sent successfully" << std::endl;
  } catch (const std::exception &e) {
    std::cerr << "Error while sending command '" << command << "': " << e.what()
              << std::endl;
    throw;
  }
}

// Callback function to process calibration results
void calibration_callback(ifm3d::Frame::Ptr frame) {
  if (frame->HasBuffer(ifm3d::buffer_id::O3R_RESULT_JSON) && !CALIBRATED) {
    auto result_json_buffer =
        frame->GetBuffer(ifm3d::buffer_id::O3R_RESULT_JSON);
    std::string result_json_string = std::string(
        result_json_buffer.ptr<char>(0),
        strnlen(result_json_buffer.ptr<char>(0), result_json_buffer.size()));
    ifm3d::json result_json = ifm3d::json::parse(result_json_string);

    // Check the calibrationState value
    int calibration_state = result_json.value("calibrationState", 0);
    if (calibration_state == 1) {
      CALIBRATED = true;
      std::cout << "Calibration successful!" << std::endl;
      std::cout << "Calibration Results:" << std::endl
                << result_json.dump(4) << std::endl; // Pretty-print JSON
    } else {
      std::cout << "Calibration failed: calibrationState = "
                << calibration_state << std::endl;
    }
  }
}

int main() {
  // IP address of the VPU
  std::string IP = "192.168.0.69"; // Default IP
  // Path to the configuration file, assuming
  // that the example is built in scc/build
  std::string config_path = "../config/scc_calibration_port2.json";

  // Create the O3R device object
  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  // Load configuration
  std::ifstream file(config_path);
  if (!file) {
    throw std::runtime_error("Failed to open config file: " + config_path);
  }
  json config = json::parse(file);
  file.close();

  // Retrieve the application instance
  auto instances = config["applications"]["instances"];
  if (instances.empty()) {
    throw std::runtime_error(
        "No applications found in the configuration file.");
  }
  std::string app_instance = instances.begin().key();
  std::cout << "Using application instance: " << app_instance << std::endl;

  // Ensure a clean start, only reseting the instance we are using
  try {
    auto current_instances = o3r->Get({"/applications/instances"});
    if (current_instances["applications"]["instances"].contains(app_instance)) {
      o3r->Reset("/applications/instances/" + app_instance);
      std::cout << "Reset application instance: " << app_instance << std::endl;
    } else {
      std::cout << "Application instance '" << app_instance
                << "' not found, skipping reset." << std::endl;
    }
  } catch (const std::exception &e) {
    std::cerr << "Error while resetting application: " << e.what() << std::endl;
  }

  // Apply configuration
  try {
    o3r->Set(config);
    std::cout << "Configuration applied successfully" << std::endl;
  } catch (const std::exception &e) {
    std::cerr << "Error while applying configuration: " << e.what()
              << std::endl;
    return 1;
  }

  // Set application to RUN state
  try {
    json run_state = {{"applications",
                       {{"instances", {{app_instance, {{"state", "RUN"}}}}}}}};
    o3r->Set(run_state);
    std::cout << "Application set to RUN state" << std::endl;
  } catch (const std::exception &e) {
    std::cerr << "Error while setting application to RUN state: " << e.what()
              << std::endl;
    return 1;
  }

  // Clear the buffer before calibration
  send_command(o3r, app_instance, "clearBuffer");

  // Setup framegrabber
  auto fg = std::make_shared<ifm3d::FrameGrabber>(
      o3r, o3r->Port(app_instance).pcic_port);
  fg->Start({ifm3d::buffer_id::O3R_RESULT_JSON});
  fg->OnNewFrame(&calibration_callback);

  // Calibrate the camera
  try {
    send_command(o3r, app_instance, "calibrate");
  } catch (const std::exception &e) {
    std::cerr << "Error during calibration: " << e.what() << std::endl;
    return 1;
  }

  if (CALIBRATED) {
    std::cout << "Calibration successful, writing to device..." << std::endl;
    // Write calibration to device
    try {
      send_command(o3r, app_instance, "writeToDevice");
    } catch (const std::exception &e) {
      std::cerr << "Error while writing calibration to device: " << e.what()
                << std::endl;
      return 1;
    }
  } else {
    std::cout << "Calibration failed, please check the camera setup."
              << std::endl;
  }

  // Stop the framegrabber
  fg->Stop();

  return 0;
}
