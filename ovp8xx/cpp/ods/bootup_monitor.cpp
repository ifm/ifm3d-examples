#include <ifm3d/device/o3r.h>

#include "bootup_monitor.h"

int main(){
    const char* IP = std::getenv("IFM3D_IP");
    if (!IP) {
        IP = ifm3d::DEFAULT_IP.c_str();
        std::clog << "Using default IP" << std::endl;        
    }
    std::clog << "IP: " << IP << std::endl;

    auto o3r = std::make_shared<ifm3d::O3R>(IP);
    BootupMonitor bootup_monitor(o3r);

    try{
        bootup_monitor.MonitorVPUBootup();
    }catch (std::runtime_error& e){
        std::cerr << e.what() << std::endl;
    }
    return 0; 
}