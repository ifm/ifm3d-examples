#include <thread>
#include <ifm3d/common/json_impl.hpp>
#include <ifm3d/device/err.h>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>

using namespace std::chrono_literals;

void PalletCallback(ifm3d::Frame::Ptr frame) {
    if (frame->HasBuffer(ifm3d::buffer_id::O3R_RESULT_JSON)){
        std::cout << "Received a frame" << std::endl;
        auto result_json_buffer = frame->GetBuffer(ifm3d::buffer_id::O3R_RESULT_JSON);
        std::string result_json_string = std::string(result_json_buffer.ptr<char>(0), strnlen(result_json_buffer.ptr<char>(0), result_json_buffer.size()));
        ifm3d::json result_json = ifm3d::json::parse(result_json_string);
        std::cout << "Detected pallet(s): " 
                  << result_json["getPallet"]["pallet"]
                  << std::endl;
    }
}

int main(){
    ////////////////////////////////
    // Device specific configuration
    ////////////////////////////////
    std::string IP = "192.168.0.69";
    std::string CAMERA_PORT = "port0";
    std::string APP_PORT = "app0";
    auto o3r = std::make_shared<ifm3d::O3R>(IP);
    
    ////////////////////////////////
    // Setup the application
    ////////////////////////////////
    try {
        o3r->Reset("/applications");
    } catch (ifm3d::Error &err) {
        std::cerr << "Error resetting the camera: " << err.what() << std::endl;
        return -1;
    }
    ifm3d::json ports_config = {
            {"ports",{
                {CAMERA_PORT, {
                    {"processing", {
                        {"extrinsicHeadToUser", {
                            {"transX", 0.0}, 
                            {"transY", 0.0}, 
                            {"transZ", 0.2}, 
                            {"rotX", 0.0}, 
                            {"rotY", 1.57}, 
                            {"rotZ", -1.57}
                        }}
                    }}
                }}
            }}
        };
    
    std::cout << "Setting port configuration:" 
              << ports_config << std::endl;
    o3r->Set(ports_config);

    ifm3d::json app_config = {
            {"applications",{
                {"instances",{
                    {APP_PORT,{
                        {"class", "pds"},
                        {"ports", {CAMERA_PORT}},
                        {"state", "IDLE"}
                    }}
                }}
            }}
        };
    std::cout << "Setting app configuration:" 
              << app_config << std::endl;
    o3r->Set(app_config);

    ////////////////////////////////
    // Setup the framegrabber to receive frames
    // when the application is triggered.
    ////////////////////////////////
    auto fg = std::make_shared<ifm3d::FrameGrabber>(o3r, o3r->Port(APP_PORT).pcic_port);
    fg->Start({ifm3d::buffer_id::O3R_RESULT_JSON});
    fg->OnNewFrame(&PalletCallback);

    ////////////////////////////////
    // Trigger the application
    ////////////////////////////////
    std::this_thread::sleep_for(2s);
    ifm3d::json getPallet_parameters = {
        {"depthHint", 1.2},
        {"palletIndex", 0}
    };
    ifm3d::json getPallet_command = {
            {"applications",{
                {"instances",{
                    {APP_PORT,{
                        {"configuration", {
                            {"customization",{
                                {"command", "getPallet"},
                                {"getPallet", getPallet_parameters}
                            }}
                        }}
                    }}
                }}
            }}
        };
    std::cout << "Triggering the volCheck command" << std::endl;
    o3r->Set(getPallet_command);

    std::this_thread::sleep_for(3s);
    fg->Stop();
    return 0;
}