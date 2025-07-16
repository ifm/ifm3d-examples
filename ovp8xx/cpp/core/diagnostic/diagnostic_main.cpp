/*
 * Copyright 2025-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 * Demonstrates how to retrieve diagnostics using the O3RDiagnostic class
 * and handle diagnostics asynchronously using a callback function.
 */
#include "diagnostic.hpp"
#include <chrono>
#include <iostream>
#include <thread>

int main() {
  const std::string ip = "192.168.0.69"; // Replace with your O3R IP address
  auto o3r = std::make_shared<ifm3d::O3R>(ip);
  O3RDiagnostic diagnostic(o3r);

  // Retrieve and display active diagnostics
  try {
    auto active_diagnostics =
        diagnostic.GetDiagnosticFiltered({{"state", "active"}});
    std::cout << "Current active diagnostics:\n"
              << active_diagnostics.dump(4)
              << "\n"; // Pretty print with 4 spaces
  } catch (const std::exception &e) {
    std::cerr << "Error retrieving active diagnostics: " << e.what() << "\n";
  }

  // Loop for 5 seconds, displaying only the relevant groups
  std::cout << "Filtering diagnostics for 5 seconds...\n";
  auto start_time = std::chrono::steady_clock::now();
  while (std::chrono::steady_clock::now() - start_time <
         std::chrono::seconds(5)) {
    try {
      auto filtered_diagnostics =
          diagnostic.GetDiagnosticFiltered({{"state", "active"}});
      auto groups = filtered_diagnostics["groups"];

      // Display the groups status for existing ports and applications
      json filtered_groups;
      for (auto &[key, value] : groups.items()) {
        if (value != "not_available") {
          filtered_groups[key] = value;
        }
      }

      std::cout << "Current active diagnostic groups (filtered):\n"
                << filtered_groups.dump(4)
                << "\n"; // Pretty print with 4 spaces
    } catch (const std::exception &e) {
      std::cerr << "Error retrieving filtered diagnostics: " << e.what()
                << "\n";
    }

    std::this_thread::sleep_for(
        std::chrono::seconds(1)); // Wait 1 second before the next iteration
  }

  // Start asynchronous diagnostic monitoring
  diagnostic.StartAsyncDiagnostics();

  // Run asynchronous monitoring until interrupted
  try {
    std::cout << "Press Ctrl+C to stop diagnostic monitoring.\n";
    while (true) {
      std::this_thread::sleep_for(std::chrono::milliseconds(100));
    }
  } catch (...) {
    diagnostic.StopAsyncDiagnostics();
    std::cout << "Stopping diagnostic monitoring.\n";
  }

  return 0;
}
