#include "config_loader.hpp"
#include <bitset>
#include <ifm3d/common/json_impl.hpp>
#include <ifm3d/device/err.h>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <thread>

using namespace std::chrono_literals;
using ifm3d::json;

// Define the flags
struct Flag {
  int bit_no;
  std::string name;
  std::string description;
  std::string application;
};

// List of flags
const std::vector<Flag> FLAGS = {
    {0, "USED_FOR_DEPTH_HINT", "Used for depth hint detection", "various"},
    {1, "ORTHO_PROJECTED", "Used for orthographic projection", "various"},
    {2, "GP_RANSAC", "Part of pallet’s face", "getPallet"},
    {3, "GT_FLOOR_PLATE", "Part of item’s floor plate", "getItem"},
    {4, "VOL_CHECK", "Pixel inside volCheck volume", "volCheck"},
    {5, "GR_BEAM_FACE", "Part of beam face", "getRack"},
    {6, "GR_BEAM_EDGE", "Part of beam edge", "getRack"},
    {7, "GR_UPRIGHT_FACE", "Part of upright face", "getRack"},
    {8, "GR_UPRIGHT_EDGE", "Part of upright edge", "getRack"},
    {9, "GR_CLEARING_VOL", "Pixel inside clearing volume", "getRack"}};

// Deserialize the flags
void DeserializeFlags(uint32_t bitmask) {
  std::cout << "Bitmask: " << std::bitset<32>(bitmask) << std::endl;
  for (const auto &flag : FLAGS) {
    bool is_set =
        (bitmask & (1 << flag.bit_no)) != 0; // Check if the bit is set
    std::cout << "Bit " << flag.bit_no << " (" << flag.name
              << "): " << (is_set ? "SET" : "NOT SET") << " - "
              << flag.description << " (Application: " << flag.application
              << ")" << std::endl;
  }
}

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

void FlagsCallback(ifm3d::Frame::Ptr frame) {
  if (frame->HasBuffer(ifm3d::buffer_id::O3R_RESULT_ARRAY2D)) {
    std::cout << "Received a frame" << std::endl;
    auto result_buffer = frame->GetBuffer(ifm3d::buffer_id::O3R_RESULT_ARRAY2D);
    // The result_buffer is a 1D bytes array, so we need to
    // reformat it into a 2D array of uint16_t
    std::vector<uint16_t> result_1D_array =
        std::vector<uint16_t>(result_buffer.ptr<uint16_t>(0),
                              result_buffer.ptr<uint16_t>(0) +
                                  result_buffer.size() / sizeof(uint16_t));
    std::vector<std::vector<uint16_t>> result_array(172,
                                                    std::vector<uint16_t>(224));
    for (int i = 0; i < 172; ++i) {
      for (int j = 0; j < 224; ++j) {
        result_array[i][j] = result_1D_array[i * 224 + j];
      }
    }
    std::cout << "Flag for pixel (100, 100): " << result_array[100][100]
              << std::endl;
  }
}

int main() {
  ////////////////////////////////////
  // Path to the configuration files
  // Note that the configuration files will be
  // copied to the build folder.
  ////////////////////////////////////
  std::string config_extrinsic_path = "configs/extrinsics.json";
  std::string config_standard_pallet = "configs/pds_minimal_config.json";
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

  // Set Extrinsic Calibration
  std::cout << "Set extrinsics calibration parameters" << std::endl;
  o3r->Set(extrinsics_config);

  // Retrieve the application instance
  auto instances = pds_config["applications"]["instances"];
  if (instances.empty()) {
    throw std::runtime_error(
        "No applications found in the configuration file.");
  }
  std::string app_instance = instances.begin().key();

  std::cout << "Set Configuration for PDS" << std::endl;
  o3r->Set(pds_config);

  // Start diagnostic monitoring
  std::this_thread::sleep_for(std::chrono::seconds(2));
  auto diag_fg = std::make_shared<ifm3d::FrameGrabber>(o3r, 50009);
  diag_fg->OnAsyncError([app_instance](int id, const std::string &message) {
    async_diagnostic_callback(message, app_instance);
  });
  std::clog << "Starting async diagnostic monitoring." << std::endl;
  diag_fg->Start({});

  ////////////////////////////////
  // Setup the framegrabber to receive frames
  // when the application is triggered.
  ////////////////////////////////
  auto fg = std::make_shared<ifm3d::FrameGrabber>(
      o3r, o3r->Port(app_instance).pcic_port);
  fg->Start({ifm3d::buffer_id::O3R_RESULT_ARRAY2D});
  fg->OnNewFrame(&FlagsCallback);

  // Set the application to idle state
  json idle_state = {
      {"applications", {{"instances", {{app_instance, {{"state", "IDLE"}}}}}}}};

  o3r->Set(idle_state);
  ////////////////////////////////
  // Trigger the application
  ////////////////////////////////
  std::this_thread::sleep_for(2s);
  json volCheck_command = {{"applications",
                            {{"instances",
                              {{app_instance,
                                {{"configuration",
                                  {{"customization",
                                    {
                                        {"command", "volCheck"},
                                    }}}}}}}}}}};
  std::cout << "Triggering the PDS application to view the flags" << std::endl;
  o3r->Set(volCheck_command);

  std::this_thread::sleep_for(3s);
  fg->Stop();
  diag_fg->Stop();
  return 0;
}
