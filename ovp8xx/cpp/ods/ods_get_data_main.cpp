/*
 * Copyright 2025-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 *
 * This example assumes that an instance of ODS is configured
 * and switched to RUN state.
 */
#include <iostream>
#include <stdexcept>
#include <thread>

#include "ods_get_data.hpp"

#include <ifm3d/common/json.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_extrinsic_calibration_correction_v1.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_info_v1.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_occupancy_grid_v1.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_polar_occupancy_grid_v1.hpp>
#include <ifm3d/device/o3r.h>

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

int main() {
  // Device specific configuration
  std::string IP = "192.168.0.69";
  auto o3r = std::make_shared<ifm3d::O3R>(IP);
  std::string app_name = "app0"; // Change to your app name

  ODSStream ods_stream(
      o3r, app_name,
      {ifm3d::buffer_id::O3R_ODS_INFO, ifm3d::buffer_id::O3R_ODS_OCCUPANCY_GRID,
       ifm3d::buffer_id::O3R_ODS_POLAR_OCC_GRID,
       ifm3d::buffer_id::O3R_ODS_EXTRINSIC_CALIBRATION_CORRECTION},
      500, 5);
  ods_stream.StartODSStream();
  std::this_thread::sleep_for(std::chrono::seconds(2));

  auto diag_fg = std::make_shared<ifm3d::FrameGrabber>(o3r, 50009);
  diag_fg->OnAsyncError([app_name](int id, const std::string &message) {
    async_diagnostic_callback(message, app_name);
  });
  std::clog << "Starting async diagnostic monitoring. \nErrors ids and "
               "descriptions will be logged."
            << std::endl;
  diag_fg->Start({});

  while (true) {
    auto zones = ods_stream.GetZones();
    auto grid = ods_stream.GetOccGrid();
    auto polar_grid = ods_stream.GetPolarOccGrid();
    auto ods_extrinsic_calibration_correction =
        ods_stream.GetExtrinsicCalibrationCorrection();

    if (zones) {
      std::clog << "-------------ODS zones data --------------------------"
                << std::endl;
      std::clog << "Current zone id used: " << zones.value().zone_config_id
                << std::endl;
      std::clog << "Zones occupancy: "
                << std::to_string(zones.value().zone_occupied[0]) << ", "
                << std::to_string(zones.value().zone_occupied[1]) << ", "
                << std::to_string(zones.value().zone_occupied[2]) << std::endl;
      std::clog << "Zones info timestamp: " << zones.value().timestamp_ns
                << std::endl;
    }

    if (grid) {
      std::clog << "--------------ODS occupancy grid data------------------"
                << std::endl;
      std::clog << "Occupancy grid image shape: " << grid.value().image.height()
                << "x" << grid.value().image.width() << std::endl;
      std::clog << "Occupancy grid timestamp: " << grid.value().timestamp_ns
                << std::endl;
    }

    if (polar_grid) {
      std::clog << "--------------ODS polar occupancy grid data ----------"
                << std::endl;
      auto distance_0degree =
          polar_grid.value().polarOccGrid[0] /
          1000.0; // distances are in mm, the 360° are divided into 675 values
      if (distance_0degree ==
          65.535) { // 65.535 is a special value for no object detected
        std::clog << "No object detected at 0° using the Polar occupancy grid"
                  << std::endl;
      } else {
        std::clog << "Distance to the first object at 0° using the Polar "
                     "occupancy grid: "
                  << distance_0degree << " m" << std::endl;
      }
    }

    if (ods_extrinsic_calibration_correction) {
      const auto &calibration_data =
          ods_extrinsic_calibration_correction.value();
      std::clog << "-------------Extrinsic Calibration Correction data "
                   "--------------------------"
                << std::endl;
      std::clog << "rot_delta_valid [x,y,z] : "
                << std::to_string(calibration_data.rot_delta_valid[0]) << ", "
                << std::to_string(calibration_data.rot_delta_valid[1]) << ", "
                << std::to_string(calibration_data.rot_delta_valid[2])
                << std::endl;
      std::clog << "rot_head_to_user [x,y,z] : "
                << std::to_string(calibration_data.rot_head_to_user[0]) << ", "
                << std::to_string(calibration_data.rot_head_to_user[1]) << ", "
                << std::to_string(calibration_data.rot_head_to_user[2])
                << std::endl;
    } else {
      std::clog << "No valid extrinsic calibration correction data available."
                << std::endl;
    }
    std::this_thread::sleep_for(std::chrono::seconds(1));
  }

  std::cout << "Finished getting data from ODS\n";
  ods_stream.StopODSStream();
  diag_fg->Stop();

  return 0;
}
