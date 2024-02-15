#include "diagnostic.hpp"
#include <ifm3d/device/o3r.h>
#include <iostream>
#include <thread>

using namespace std::chrono_literals;
using namespace ifm3d::literals;

void CustomCallback(int id_, std::string message_){
  std::clog << "Custom callback: " << id_ << " " << message_ << std::endl;
}

int main() {
  auto o3r = std::make_shared<ifm3d::O3R>();
  // To log to file, use diagnostic(o3r, true, "file_name").
  // Log outputs will be redirected both to the file and
  // to the console.
  auto log_to_file = false;
  O3RDiagnostic diagnostic(o3r, log_to_file);

  ////////////////////////////////////////////////
  // Examples on how to retrieve the diagnostic
  // active and/or dormant.
  ////////////////////////////////////////////////
  // Using ifm3d::json::object()
  std::clog << "All current diagnostics:\n"
            << diagnostic.GetDiagnosticFiltered(ifm3d::json::object()).dump(4)
            << std::endl;

  std::clog << "Active diagnostics:\n"
            << diagnostic.GetDiagnosticFiltered(
                   ifm3d::json::parse(R"({"state": "active"})")).dump(4)
            << std::endl
            << std::endl
            << std::endl;

  ////////////////////////////////////////////////
  // Start the asynchronous diagnostic monitoring
  // and display errors for "d" seconds.
  ////////////////////////////////////////////////

  diagnostic.StartAsyncDiag(CustomCallback);
  // You can also call the function without a custom 
  // callback, in which case the default callback will
  // be used:
  // diagnostic.StartAsyncDiag();

  std::this_thread::sleep_for(20s);

  diagnostic.StopAsyncDiag();

  return 0;
}
