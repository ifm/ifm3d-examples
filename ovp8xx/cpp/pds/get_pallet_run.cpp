#include "config_loader.hpp"
#include <atomic>
#include <condition_variable>
#include <csignal>
#include <fstream>
#include <ifm3d/common/json.hpp>
#include <ifm3d/device/err.h>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream> // Added for cout and cerr
#include <mutex>
#include <queue>
#include <thread>

using namespace std::chrono_literals;
using ifm3d::json;

std::atomic<bool> keep_running(true);

// Thread-safe queue class
template <typename T> class ThreadSafeQueue {
private:
  std::queue<T> queue;
  std::mutex mtx;
  std::condition_variable cv;

public:
  void Push(T value) {
    std::lock_guard<std::mutex> lock(mtx);
    queue.push(std::move(value));
    cv.notify_one();
  }

  bool TryPop(T &value) {
    std::unique_lock<std::mutex> lock(mtx); // Use unique_lock to allow cv.wait
    if (queue.empty()) {
      return false;
    }
    value = std::move(queue.front());
    queue.pop();
    return true;
  }
};

ThreadSafeQueue<ifm3d::json> resultQueue;

// Diagnostic callback function
void async_diagnostic_callback(const std::string &message,
                               const std::string &app_name) {
  using ifm3d::json;

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
void PalletCallback(ifm3d::Frame::Ptr frame) {
  if (frame->HasBuffer(ifm3d::buffer_id::O3R_RESULT_JSON)) {
    auto result_json_buffer =
        frame->GetBuffer(ifm3d::buffer_id::O3R_RESULT_JSON);
    std::string result_json_string = std::string(
        result_json_buffer.ptr<char>(0),
        strnlen(result_json_buffer.ptr<char>(0), result_json_buffer.size()));

    try {
      ifm3d::json result_json = ifm3d::json::parse(result_json_string);
      resultQueue.Push(result_json);
    } catch (const std::exception &e) {
      std::cerr << "Exception: " << e.what() << std::endl;
    }
  }
}

void ProcessResults() {
  ifm3d::json result;
  while (keep_running) {
    if (resultQueue.TryPop(result)) {
      if (result.contains("getPallet") &&
          result["getPallet"].contains("pallet")) {
        auto pallets = result["getPallet"]["pallet"];
        if (pallets.is_array()) {
          std::cout << "Number of pallets detected: " << pallets.size()
                    << std::endl;

          for (size_t i = 0; i < pallets.size(); ++i) {
            std::cout << "Pallet " << i + 1 << ": " << pallets[i].dump(4)
                      << std::endl;
          }
        } else {
          std::cout << "No pallets detected or invalid format." << std::endl;
        }
      }
    }
    std::this_thread::sleep_for(100ms); // Add a small delay
  }
  std::cout << "Processing results thread finished" << std::endl;
}

int main() {
  ////////////////////////////////////
  // Path to the configuration files
  // Note that the configuration files will be
  // copied to the build folder.
  ////////////////////////////////////
  std::string config_extrinsic_path = "configs/extrinsics.json";
  std::string config_standard_pallet = "configs/pds_getPallet.json";
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
  std::cout << "Set Configuration for getPallet" << std::endl;
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
  std::cout << "Setting PDS app to RUN state" << std::endl;

  o3r->Set(ifm3d::json{
      {"applications", {{"instances", {{app_instance, {{"state", "RUN"}}}}}}}});

  auto fg = std::make_shared<ifm3d::FrameGrabber>(
      o3r, o3r->Port(app_instance).pcic_port);
  fg->Start({ifm3d::buffer_id::O3R_RESULT_JSON});
  fg->OnNewFrame(&PalletCallback);

  std::this_thread::sleep_for(2s);

  ifm3d::json getPallet_command = {
      {"applications",
       {{"instances",
         {{app_instance,
           {{"configuration",
             {{"customization", {{"command", "getPallet"}}}}}}}}}}}};

  std::cout << "Triggering the getPallet command" << std::endl;
  o3r->Set(getPallet_command);

  std::cout << "Starting processing thread for 5 seconds" << std::endl;

  std::this_thread::sleep_for(1s);

  std::thread processing_thread(ProcessResults);

  std::this_thread::sleep_for(5s); // let the thread run for 5 seconds.

  keep_running = false; // signal the thread to stop

  processing_thread.join();

  fg->Stop();
  diag_fg->Stop();
  return 0;
}
