/*
 * Copyright 2021-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 *
 * This example assumes that an instance of ODS is configured
 * and switched to RUN state.
 */
#include <iostream>
#include <thread>
#include <stdexcept>

#include "ods_config.h"
#include "ods_get_data.h"

#include <ifm3d/device/o3r.h>
#include <ifm3d/deserialize/struct_o3r_ods_info_v1.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_occupancy_grid_v1.hpp>

int main()
{

    ///////////////////////////////////////////////////
    // Variables needed for the example
    ///////////////////////////////////////////////////
    std::string config_extrinsic_path = "../Configs/extrinsic_one_head.json";
    std::string config_app_path = "../Configs/ods_one_head_config.json";


    // Declare the device object (one object only, corresponding to the VPU)
    auto o3r = std::make_shared<ifm3d::O3R>();

    ////////////////////////////////////////////////
    // Reset the configuration so that we configure
    // exactly what this example expects.
    ////////////////////////////////////////////////
    std::clog << "Resetting the applications" << std::endl;
    o3r->Reset({"/applications"});

    try {
        std::clog << "Trying to get data from app before instantiating" << std::endl;
        ODSStream ods_stream(o3r, "app0", {ifm3d::buffer_id::O3R_ODS_INFO, ifm3d::buffer_id::O3R_ODS_OCCUPANCY_GRID}, 500);
    } catch (...) { // Failing silently to continue with the tutorial.
        std::clog << "ODSStream cannot be configured with inexistent app0.\n"
                  << "This is expected, continuing with the example."
                  << std::endl;
    }

    ODSConfig ods_config(o3r);
    // TODO: change path to config file
    // Assuming a camera facing forward, label up,
    // 60 cm above the floor.
    // We keep the extrinsic calibration and the ODS configuration
    // separate for clarity. You can keep all configurations
    // in one file if necessary.
    ods_config.SetConfigFromFile(config_extrinsic_path);
    ods_config.SetConfigFromFile(config_app_path);
    // We did not start the application when configuring it,
    // so we need to start it now (change state to "RUN")
    ods_config.SetConfigFromStr(R"({"applications": {"instances": {"app0": {"state": "RUN"}}}})");

    ////////////////////////////////////////////////
    // Instantiate the ODSStream object: we expect an
    // app called "app0". If your app is different,
    // change the app name below.
    ////////////////////////////////////////////////
    std::string app_name = "app0"; // HERE change to your app name
    // Here we are starting data streams for both the
    // zones and the occupancy grid. This can be changed
    // by removing unwanted data streams from the buffer
    // list.
    ODSStream ods_stream(o3r, app_name, {ifm3d::buffer_id::O3R_ODS_INFO, ifm3d::buffer_id::O3R_ODS_OCCUPANCY_GRID}, 500);
    ods_stream.StartODSStream();
    std::this_thread::sleep_for(std::chrono::seconds(2));

    // Loop and display current zones and occupancy grid information
    // for duration d
    int d = 5;
    for (auto start = std::chrono::steady_clock::now(), now = start; now < start + std::chrono::seconds{d}; now = std::chrono::steady_clock::now()) {
        auto zones = ods_stream.GetZones();
        std::clog << "Current zone occupancy:\n"
                  << std::to_string(zones.zone_occupied[0]) << ", "
                  << std::to_string(zones.zone_occupied[1]) << ", "
                  << std::to_string(zones.zone_occupied[2])
                  << std::endl;
        auto grid = ods_stream.GetOccGrid();
        std::clog << "Current occupancy grid's middle cell:\n"
                  << std::to_string(grid.image.at<uint8_t>(100, 100))
                  << std::endl;
    }

    ods_stream.StopODSStream();

    return 0;
}
