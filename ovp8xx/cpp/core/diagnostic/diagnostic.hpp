/*
 * Shared functionality for O3R diagnostics.
 */
#ifndef DIAGNOSTICS_HPP
#define DIAGNOSTICS_HPP

#include <chrono>
#include <ifm3d/common/json.hpp>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <stdexcept>
#include <string>
#include <thread>

using ifm3d::json;

class O3RDiagnostic {
public:
  O3RDiagnostic(std::shared_ptr<ifm3d::O3R> o3r) : o3r_(o3r) {
    diag_fg_ = std::make_shared<ifm3d::FrameGrabber>(o3r_, 50009);
  }

  void StartAsyncDiagnostics() {
    diag_fg_->OnAsyncError(async_diagnostic_callback);
    std::cout << "Starting async diagnostic monitoring. Errors and "
                 "descriptions will be logged.\n";
    diag_fg_->Start({});
  }

  void StopAsyncDiagnostics() {
    std::cout << "Stopping async diagnostic monitoring.\n";
    diag_fg_->Stop();
  }

  json GetDiagnosticFiltered(const json &filter_mask = {}) {
    try {
      std::cout << "Polling O3R diagnostic data with filter: "
                << filter_mask.dump() << "\n";
      return o3r_->GetDiagnosticFiltered(filter_mask);
    } catch (const std::exception &e) {
      std::cerr << "Error when getting diagnostic data: " << e.what() << "\n";
      throw;
    }
  }

  static void async_diagnostic_callback(int id, const std::string &message) {
    json diagnostic = json::parse(message);

    // Extract severity levels
    const std::vector<std::string> severity_levels = {"critical", "major",
                                                      "minor", "info"};
    const std::string default_severity = "major";

    // Check if events exist
    if (!diagnostic.contains("events") || diagnostic["events"].empty()) {
      std::cout << "No diagnostic events found.\n";
      return;
    }

    // Extract events and filter by severity
    auto events = diagnostic["events"];
    for (const auto &event : events) {
      json filtered_diag = {{"id", event["id"]},
                            {"name", event["name"]},
                            {"severity", event["severity"]},
                            {"description", event["description"]},
                            {"source", event["source"]},
                            {"state", event["state"]},
                            {"timestamp", diagnostic["timestamp"]}};

      // Check severity and print critical diagnostics
      if (filtered_diag["severity"] == "critical") {
        std::cout << "⚠️ Critical diagnostic appeared! Stop the robot and "
                     "follow the handling strategy.\n";
      } // here you can add your own handling strategy and stopping the robot

      // Print JSON with indentation (pretty print)
      std::cout << "Received diagnostic message:\n"
                << filtered_diag.dump(4) << "\n"; // '4' is indentation level
    }
  }

private:
  std::shared_ptr<ifm3d::O3R> o3r_;
  std::shared_ptr<ifm3d::FrameGrabber> diag_fg_;
};

#endif // DIAGNOSTICS_HPP
