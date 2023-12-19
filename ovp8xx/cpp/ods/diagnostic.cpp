#include <iostream>
#include <ifm3d/device/o3r.h>
#include "diagnostic.h"

using namespace ifm3d::literals;

int main()
{
    auto o3r = std::make_shared<ifm3d::O3R>();
    // To log to file, use diagnostic(o3r, true, "file_name").
    // Log outputs will be redirected both to the file and 
    // to the console.
    O3RDiagnostic diagnostic(o3r);

    ////////////////////////////////////////////////
    // Examples on how to retrieve the diagnostic
    // active and/or dormant.
    ////////////////////////////////////////////////
    // Using ifm3d::json::object() 
    std::clog << "All current diagnostics:\n"
              << diagnostic.GetDiagnosticFiltered(ifm3d::json::object()) << std::endl;

    std::clog << "Active diagnostics:\n"
              << diagnostic.GetDiagnosticFiltered(ifm3d::json::parse(R"({"state": "active"})"))
              << std::endl << std::endl << std::endl;

    ////////////////////////////////////////////////
    // Start the asynchronous diagnostic monitoring
    // and display errors for "d" seconds.
    ////////////////////////////////////////////////

    diagnostic.StartAsyncDiag();

    // Loop for duration "d"
    int d = 5;
    for (auto start = std::chrono::steady_clock::now(), now = start; now < start + std::chrono::seconds{d}; now = std::chrono::steady_clock::now())
    {
        // Do nothing, just wait for the specified duration
    }

    diagnostic.StopAsyncDiag();

    return 0;
}
