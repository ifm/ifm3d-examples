#include <iostream>
#include <chrono>
#include <string>
#include <cstring>
#include <stdexcept>
#include <thread>
#include <ifm3d/device/o3r.h>
#include <ifm3d/device/err.h>
using namespace ifm3d::literals;

class BootupMonitor{
public:
    ifm3d::O3R::Ptr o3r;
    const int timeout; // in seconds
    const std::string IP;
    const int wait_time; // in seconds

    BootupMonitor(ifm3d::O3R::Ptr o3r_, int timeout_ = 25, int wait_time_ = 1 ) :
        o3r(o3r_),
        timeout(timeout_),
        IP(o3r->IP()),
        wait_time(wait_time_)
    {
        
    }
    bool MonitorVPUBootup()
    {
        std::clog << "Monitoring bootup sequence: ready to connect." << std::endl;
        auto start = std::chrono::steady_clock::now();
        ifm3d::json config;
        do{
            try{
                config = o3r->Get();
                std::clog << "Connected." << std::endl;
            }catch(ifm3d::Error& e){
                std::clog << "Awaiting data from VPU..." << std::endl;
            }
            if (!config.empty()){
                std::clog << "Checking the init stages." << std::endl;
                auto conf_init_stages = config["/device/diagnostic/confInitStages"_json_pointer];
                std::clog << conf_init_stages << std::endl;
                for (auto it : conf_init_stages)
                {
                    if (it == "applications"){
                        std::clog << "VPU fully booted." << std::endl;
                        RetrieveBootDiagnostic_();
                        return true;
                    }
                    if (it == "ports"){
                        std::clog << "Ports recognized." << std::endl;
                    }
                    else if (it == "device")
                    {
                        std::clog << "Device recognized." << std::endl;
                    }
                }
            }
            std::this_thread::sleep_for(std::chrono::seconds(wait_time));

        }while(std::chrono::steady_clock::now() - start < std::chrono::seconds(timeout));
        throw std::runtime_error("Process timed out waiting for the VPU to boot.");
    }

private:
    void RetrieveBootDiagnostic_()
    {
        auto active_diag = o3r->GetDiagnosticFiltered(ifm3d::json::parse(R"({"state": "active"})"))["/events"_json_pointer];
        for (auto error = active_diag.begin(); error != active_diag.end(); ++error)
        {
            std::clog << "\n//////////////////////////////////" << std::endl;
            std::clog << *error << std::endl;
        }
    }
};