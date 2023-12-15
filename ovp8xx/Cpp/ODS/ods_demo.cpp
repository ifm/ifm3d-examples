#include <iostream>
#include <fstream>
#include <chrono>
#include <thread>
#include <cstdint>

#include "ods_config.h"
#include "ods_get_data.h"
#include "diagnostic.h"
// #define JSON_USE_GLOBAL_UDLS 0
// #include <nlohmann/json.hpp>

#include <ifm3d/device/o3r.h>
using namespace ifm3d::literals;

int main()
{
    ////////////////////////////////////////////////
    // Define the variables used in the example
    ////////////////////////////////////////////////
    // O3R and ODS configuration
    // Getting IP from environment variable
    const char* IP = std::getenv("IFM3D_IP");
    if (!IP) {
        IP = ifm3d::DEFAULT_IP.c_str();
        std::clog << "Using default IP" << std::endl;        
    }
    std::clog << "IP: " << IP << std::endl;

    ifm3d::FrameGrabber::BufferList buffer_list = {ifm3d::buffer_id::O3R_ODS_INFO, ifm3d::buffer_id::O3R_ODS_OCCUPANCY_GRID};
    int timeout_ms = 500; // Timeout used when retrieving data
    // Config file for extrinsic calibrations and apps
    std::string config_extrinsic_path = "../Configs/extrinsic_two_heads.json";
    std::string config_app_path = "../Configs/ods_changing_views_config.json";
    // Data display configuration
    int step = 5;         // Used to reduce the frequency of the data displayed
    int d = 5;            // How long data will be displayed for each app
    // Logging configuration
    bool log_to_file = false;
    const std::string& log_file_name = "ODS_logfile.txt";
    
    std::ofstream logFile;
    std::streambuf* consoleBuffer = std::clog.rdbuf();
    std::clog.rdbuf(consoleBuffer);
    if (log_to_file)
    {
        logFile.open(log_file_name, std::ios::app);  // Open the log file
        // Check if the file opened successfully
        if (!logFile.is_open())
        {
            std::cerr << "Failed to open log file: " << log_file_name << std::endl;
            return 1;  // Return an error code or handle the error appropriately
        }

        std::streambuf* fileBuffer = logFile.rdbuf();
        // Redirect std::clog to the log file
        std::clog.rdbuf(fileBuffer);
    }

    auto o3r = std::make_shared<ifm3d::O3R>(IP);

    // TODO: bootup monitoring

    ////////////////////////////////////////////////
    // Check the diagnostic for any active errors.
    ////////////////////////////////////////////////
    O3RDiagnostic diagnostic(o3r);
    ifm3d::json::json_pointer p("/events");
    ifm3d::json active_diag = diagnostic.GetDiagnosticFiltered(ifm3d::json::parse(R"({"state":"active"})"))[p];

    for (auto error = active_diag.begin(); error != active_diag.end(); ++error)
    {
        std::clog << "\n//////////////////////////////////" << std::endl;
        std::clog << *error << std::endl;
    }
    std::clog << "Review any active errors before continuing" << std::endl;

    do
    {
        std::clog << '\n' << "Press \"ENTER\" when ready to continue...";
    } while (std::cin.get() != '\n');

    std::clog << "Continuing with the tutorial" << std::endl;

    ////////////////////////////////////////////////
    // Start the asynchronous diagnostic
    ////////////////////////////////////////////////
    diagnostic.StartAsyncDiag();

    ////////////////////////////////////////////////
    // Configure two applications (forward and back)
    ////////////////////////////////////////////////
    ODSConfig ods_config(o3r);
    o3r->Reset("/applications");
    ods_config.SetConfigFromFile(config_extrinsic_path);
    ods_config.SetConfigFromFile(config_app_path);

    // Verifying the proper instantiation of the app and list of ports
    std::string j_string = "/applications/instances";
    ifm3d::json::json_pointer j(j_string);
    auto app = o3r->Get({j_string})[j].begin().key();
    std::clog << "Instantiated app: " << app << std::endl;


    std::string str_ports = "/applications/instances/" + app + "/ports";
    ifm3d::json::json_pointer j2(str_ports);
    auto ports = o3r->Get({str_ports})[j2];
    std::clog << "Ports:" << ports << std::endl;

    /////////////////////////////////////////////////
    // Start streaming data from forward view (port2)
    /////////////////////////////////////////////////
    // Set the app to "RUN" state
    ods_config.SetConfigFromStr(R"({"applications": {"instances": {")" + app + R"(": {"state": "RUN"}}}})");

    ODSStream ods_stream(o3r, app, buffer_list, timeout_ms);
    ods_stream.StartODSStream();
    std::this_thread::sleep_for(std::chrono::seconds(1));

    // Print out every 5th dataset until stopped
    int count = 0;
    for (auto start = std::chrono::steady_clock::now(), now = start; now < start + std::chrono::seconds{d}; now = std::chrono::steady_clock::now())
    {
        auto zones = ods_stream.GetZones();
        auto grid = ods_stream.GetOccGrid();

        if (count % step == 0)
        {
            std::clog << "Current zone occupancy:\n"
                      << std::to_string(zones.zone_occupied[0]) << ", "
                      << std::to_string(zones.zone_occupied[1]) << ", "
                      << std::to_string(zones.zone_occupied[2])
                      << std::endl;
            std::clog << "Current occupancy grid's middle cell:\n"
                      << std::to_string(grid.image.at<uint8_t>(100, 100))
                      << std::endl;
        }
        count++;
    }

    //////////////////////////////////////////////////
    // Start streaming data from backward view (port3)
    //////////////////////////////////////////////////  
    // Set the app to "RUN" state
    ods_config.SetConfigFromStr(R"({"applications": {"instances": {")" + app + R"(": {"configuration": {"activePorts":[)" + to_string(ports[1]) + R"(]}}}}})");

    // Print out every 5th dataset until stopped
    count = 0;
    for (auto start = std::chrono::steady_clock::now(), now = start; now < start + std::chrono::seconds{d}; now = std::chrono::steady_clock::now())
    {
        auto zones = ods_stream.GetZones();
        auto grid = ods_stream.GetOccGrid();

        if (count % step == 0)
        {
            std::clog << "Current zone occupancy:\n"
                      << std::to_string(zones.zone_occupied[0]) << ", "
                      << std::to_string(zones.zone_occupied[1]) << ", "
                      << std::to_string(zones.zone_occupied[2])
                      << std::endl;
            std::clog << "Current occupancy grid's middle cell:\n"
                      << std::to_string(grid.image.at<uint8_t>(100, 100))
                      << std::endl;
        }
        count++;
    }

    ods_stream.StopODSStream();
    // Set the app to "CONF" to save energy
    ods_config.SetConfigFromStr(R"({"applications": {"instances": {")"+ app + R"(": {"state": "CONF"}}}})");

    // Stop streaming diagnostic data and exit
    diagnostic.StopAsyncDiag();

    // Close the log file
    if (log_to_file)
    {
        logFile.close();
    }

    return 0;
}
