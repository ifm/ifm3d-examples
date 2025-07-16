#include "config_loader.hpp"
#include <ifm3d/common/json_impl.hpp>
#include <ifm3d/device/err.h>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <thread>

using namespace std::chrono_literals;
using ifm3d::json;

// Diagnostic callback function
void async_diagnostic_callback(const std::string &message,
                               const std::string &app_name) {
  // Parse the diagnostic message
  json diagnostic = json::parse(message);

  // Extract groups and check the status of the specified application
  auto groups = diagnostic.value("groups", json::object());
  std::string app_status = groups.value(app_name, "unknown");

  if (app_status != "not_available" && app_status != "no_incident") {
    std::cout << "\nNew Diagnostic: The status of application '" << app_name
              << "': " << app_status << std::endl;

    // Check if the application is in a critical state
    if (app_status == "critical" || app_status == "major") {
      std::cout << "⚠️ Application '" << app_name << "' is in a " << app_status
                << " error state!" << std::endl;
    }
  }
}

// Callback function when a new frame receieved from PDS Application instance
void VolumeCallback(ifm3d::Frame::Ptr frame) {
  if (frame->HasBuffer(ifm3d::buffer_id::O3R_RESULT_JSON)) {
    std::cout << "Received a frame" << std::endl;
    auto result_json_buffer =
        frame->GetBuffer(ifm3d::buffer_id::O3R_RESULT_JSON);
    std::string result_json_string = std::string(
        result_json_buffer.ptr<char>(0),
        strnlen(result_json_buffer.ptr<char>(0), result_json_buffer.size()));
    ifm3d::json result_json = ifm3d::json::parse(result_json_string);
    std::cout << "Nearest X: " << result_json["volCheck"]["nearestX"]
              << std::endl
              << "Number of pixels in the volume: "
              << result_json["volCheck"]["numPixels"] << std::endl;
  }
}

int main() {
  ////////////////////////////////////
  // Path to the configuration files
  // Note that the configuration files will be
  // copied to the build folder.
  ////////////////////////////////////
  std::string config_extrinsic_path = "configs/extrinsics.json";
  std::string config_standard_pallet = "configs/pds_volCheck.json";
  json extrinsics_config = ConfigLoader::LoadConfig(config_extrinsic_path);
  json pds_config = ConfigLoader::LoadConfig(config_standard_pallet);

  // Device specific configuration
  std::string IP = "192.168.0.69";
  auto o3r = std::make_shared<ifm3d::O3R>(IP);

  // Reset applications
  try {
    o3r->Reset("/applications");
  } catch (ifm3d::Error &err) {
    std::cerr << "Reset failed: " << err.what() << std::endl;
    return -1;
  }

  // Retrieve app instance from the loaded config
  const auto &instances = pds_config["applications"]["instances"];
  std::string app_instance = instances.begin().key();

  // Set the configuration files
  std::cout << "Set extrinsics calibration parameters" << std::endl;
  o3r->Set(extrinsics_config);
  std::cout << "Set PDS Configuration" << std::endl;
  o3r->Set(pds_config);

  // Start diagnostic monitoring
  std::this_thread::sleep_for(std::chrono::seconds(2));
  auto diag_fg = std::make_shared<ifm3d::FrameGrabber>(o3r, 50009);
  diag_fg->OnAsyncError([](int id, const std::string &message) {
    async_diagnostic_callback(message, "app0");
  });
  std::clog << "Starting async diagnostic monitoring." << std::endl;
  diag_fg->Start({});

  // Set PDS Application state
  std::cout << "Setting PDS app to IDLE state:" << std::endl;

  o3r->Set(
      ifm3d::json{{"applications",
                   {{"instances", {{app_instance, {{"state", "IDLE"}}}}}}}});

  ////////////////////////////////
  // Setup the framegrabber to receive frames
  // when the application is triggered.
  ////////////////////////////////
  auto fg = std::make_shared<ifm3d::FrameGrabber>(
      o3r, o3r->Port(app_instance).pcic_port);
  fg->Start({ifm3d::buffer_id::O3R_RESULT_JSON});
  fg->OnNewFrame(&VolumeCallback);

  ////////////////////////////////
  // Trigger the application
  ////////////////////////////////
  std::this_thread::sleep_for(2s);
  ifm3d::json volCheck_command = {
      {"applications",
       {{"instances",
         {{app_instance,
           {{"configuration",
             {{"customization", {{"command", "volCheck"}}}}}}}}}}}};

  std::cout << "Triggering the volCheck command" << std::endl;
  o3r->Set(volCheck_command);

  std::this_thread::sleep_for(3s);
  fg->Stop();
  diag_fg->Stop();
  return 0;
}
