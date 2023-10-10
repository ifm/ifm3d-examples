/*
 * Copyright 2021-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

// This example showcases how to configure an application
// using the ifm3d API and provides utilities for verbose
// reporting of JSON syntax errors.
#include <cstdlib>
#include <iostream>
#include "ods_config.h"

#include <ifm3d/device/o3r.h>
#include <ifm3d/device/err.h>

int main()
{
    ///////////////////////////////////////////////////
    // Variables needed for the example
    ///////////////////////////////////////////////////
    std::string config_extrinsic_path = "../Configs/extrinsic_one_head.json";
    std::string config_app_path = "../Configs/ods_one_head_config.json";

    // Get the IP address from the environment variable
    // If not defined, use the default IP
    const char* IP = std::getenv("IFM3D_IP");
    if (!IP) {
        IP = ifm3d::DEFAULT_IP.c_str();
        std::clog << "Using default IP" << std::endl;
    }
    std::clog << "IP: " << IP << std::endl;

    // Declare the device object (one object only, corresponding to the VPU)
    auto o3r = std::make_shared<ifm3d::O3R>(IP);

    ///////////////////////////////////////////////
    // Examples of getting configuration snippets
    ///////////////////////////////////////////////
    // Here we expect a fully booted system.
    // Get the full configuration
    std::clog << "Getting full config" << std::endl;
    std::clog << std::setw(4) << o3r->Get() << std::endl;

    // Get a subset of the configuration
    std::clog << "Getting partial config" << std::endl;
    std::clog << std::setw(4) << o3r->Get({"/device/swVersion/firmware"}) << std::endl;

    // Get multiple subsets of the configuration
    std::clog << "Getting multiple partial configs" << std::endl;
    std::clog << std::setw(4) << o3r->Get({"/device/swVersion/firmware",
                                            "/device/status",
                                            "/ports/port0/info"}) << std::endl;

    // Throw an exception if retrieving config in the wrong path
    std::clog << "Getting config for wrong path" << std::endl;
    try {
        o3r->Get({"/device/wrongKey"});
    }
    catch (const ifm3d::Error& ex) {
        std::clog << "Caught exception: " << ex.message() << std::endl;
        std::clog << "This was expected. Continuing on with the tutorial." << std::endl;
    }

    std::clog << "Finished getting configurations" << std::endl;

    ///////////////////////////////////////////////
    // Examples of setting configuration snippets
    ///////////////////////////////////////////////
    // We use a custom class to provide configuration
    // facilities and additional error handling.
    // The user could directly use the ifm3d library
    // native calls to set the configuration.
    ODSConfig configurator(o3r);
    
    std::clog << "Setting test configurations:" << std::endl;
    configurator.SetConfigFromStr(R"(
        {"device": { "info": { "description": "I will use this O3R to change the world"}}})");

    // Set two configurations at the same time
    configurator.SetConfigFromStr(R"(
        {"device": {
            "info": {
                "name": "my_favorite_o3r"
            }
        },
        "ports": {
            "port0": {
                "info": {
                    "name": "my_favorite_port"
                }
            }
        }
        }
    )");

    // We expect that this example is run from the Cpp/Examples/build folder.
    // Update the path to the config files if using a different setup.
    configurator.SetConfigFromFile(config_extrinsic_path);
    configurator.SetConfigFromFile(config_app_path);

    try {
        configurator.SetConfigFromFile("/non/existent/file.json");
    }
    catch (...) {
        std::clog << "Error caught while configuring from a non-existent file.\n"
                  << "This is expected, continuing with the example.";
                }

    std::clog << "You are done with the configuration tutorial!" << std::endl;

    return 0;
}
