#include <iostream>
#include <queue>
#include <chrono>
#include <thread>
#include <stdexcept>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <ifm3d/deserialize/struct_o3r_ods_info_v1.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_occupancy_grid_v1.hpp>

using namespace ifm3d::literals;

class ODSDataQueue {
public:
    std::queue<ifm3d::Buffer> zones_queue;
    std::queue<ifm3d::Buffer> occ_grid_queue;

    void AddFrame(ifm3d::Frame::Ptr frame) {
        if (frame->HasBuffer(ifm3d::buffer_id::O3R_ODS_INFO)) {
            zones_queue.push(frame->GetBuffer(ifm3d::buffer_id::O3R_ODS_INFO));
        }
        if (frame->HasBuffer(ifm3d::buffer_id::O3R_ODS_OCCUPANCY_GRID)) {
            occ_grid_queue.push(frame->GetBuffer(ifm3d::buffer_id::O3R_ODS_OCCUPANCY_GRID));
        }
    }
    ifm3d::ODSInfoV1 GetZones() {
        // Calling this function on an empty queue will cause undefined behavior.
        auto zones = ifm3d::ODSInfoV1::Deserialize(zones_queue.front());
        zones_queue.pop();
        return zones;
    }
    ifm3d::ODSOccupancyGridV1 GetOccGrid() {
        // Calling this function on an empty queue will cause undefined behavior.
        auto grid = ifm3d::ODSOccupancyGridV1::Deserialize(occ_grid_queue.front());
        occ_grid_queue.pop();
        return grid;
    }
};

class ODSStream {
public:

    ifm3d::O3R::Ptr o3r;
    std::string app_name;
    ifm3d::FrameGrabber::Ptr fg;
    ifm3d::FrameGrabber::BufferList buffer_ids = { ifm3d::buffer_id::O3R_ODS_INFO,
                                                   ifm3d::buffer_id::O3R_ODS_OCCUPANCY_GRID };
    ODSDataQueue data_queue;
    int timeout = 500; //Timeout in milliseconds

    ODSStream(ifm3d::O3R::Ptr o3r_,
              std::string app_name_,
              ifm3d::FrameGrabber::BufferList buffer_ids_,
              int timeout_) {
        o3r = o3r_;
        app_name = app_name_;
        timeout = timeout_;
        std::string j_string = "/applications/instances/" + app_name + "/data/pcicTCPPort";
        ifm3d::json::json_pointer j(j_string);
        auto FG_PCIC_PORT = o3r->Get({ j_string })[j];
        fg = std::make_shared<ifm3d::FrameGrabber>(o3r, FG_PCIC_PORT);
    }
    void StartODSStream() {
        std::clog << "Starting data stream" << std::endl;
        fg->Start(buffer_ids);
        fg->OnNewFrame([this](auto frame) {
            this->data_queue.AddFrame(frame);
        });
    }
    void StopODSStream() {
        std::clog << "Stopping data stream" << std::endl;
        fg->Stop();
    }
    ifm3d::ODSInfoV1 GetZones() {
        auto start = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
        while (std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count() - start < timeout) {
            if (!data_queue.zones_queue.empty()) {
                auto zones = data_queue.GetZones();
                return zones;
            }
        }
        throw std::runtime_error("Timeout error while getting zones.\n");
    }
    ifm3d::ODSOccupancyGridV1 GetOccGrid() {
        auto start = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::system_clock::now().time_since_epoch()).count();
        while (std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::system_clock::now().time_since_epoch()).count() - start < timeout) {
            if (!data_queue.occ_grid_queue.empty()) {
                auto occ_grid = data_queue.GetOccGrid();
                return occ_grid;
            }
        }
        throw std::runtime_error("Timeout error while getting occupancy grid.\n");
    }

};
