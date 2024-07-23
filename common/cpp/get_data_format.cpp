/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <chrono>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <ifm3d/device.h>
#include <ifm3d/device/device.h>
#include <ifm3d/device/o3r.h>
#include <ifm3d/device/o3d.h>
#include <ifm3d/device/o3x.h>
#include <ifm3d/fg.h>

using namespace std::chrono_literals;

// Helper function to display the pixel format as a string
// instead of the int returned in the ifm3d::pixel_format enum.
std::string pixel_format_to_string(ifm3d::pixel_format format) {
    switch (format) {
        case ifm3d::pixel_format::FORMAT_8U: return "FORMAT_8U";
        case ifm3d::pixel_format::FORMAT_8S: return "FORMAT_8S";
        case ifm3d::pixel_format::FORMAT_16U: return "FORMAT_16U";
        case ifm3d::pixel_format::FORMAT_16S: return "FORMAT_16S";
        case ifm3d::pixel_format::FORMAT_32U: return "FORMAT_32U";
        case ifm3d::pixel_format::FORMAT_32S: return "FORMAT_32S";
        case ifm3d::pixel_format::FORMAT_32F: return "FORMAT_32F";
        case ifm3d::pixel_format::FORMAT_64U: return "FORMAT_64U";
        case ifm3d::pixel_format::FORMAT_64F: return "FORMAT_64F";
        case ifm3d::pixel_format::FORMAT_16U2: return "FORMAT_16U2";
        case ifm3d::pixel_format::FORMAT_32F3: return "FORMAT_32F3";
        default: return "Unknown format";
    }
}

int main() {
    // EDIT FOR YOUR CONFIGURATION
    std::string IP = "192.168.0.69";

    // Declare the device object
    auto device = ifm3d::Device::MakeShared(IP);
    
    ///////////////////////////////////
    // Check the device type so we can 
    // connect to the proper port.
    ///////////////////////////////////
    auto device_type = device->WhoAmI();
    uint16_t pcic_port = 0;
    if (device_type == ifm3d::Device::device_family::O3R){
        auto o3r = std::make_shared<ifm3d::O3R>(IP);
        for (const auto &port : o3r->Ports()) {
            if (port.type == "3D") {
            std::cout << "Using first available 3D port: " << port.port << std::endl;
            pcic_port = port.pcic_port;
            break;
            }
        }
        if (pcic_port == 0){
            throw std::invalid_argument("No 3D port available");
        }
    }        
    else if (device_type == ifm3d::Device::device_family::O3D or device_type == ifm3d::Device::device_family::O3X){
        pcic_port = std::stoi(device->DeviceParameter("PcicTcpPort"));
    }
    else{
        throw std::invalid_argument("Unknown device type");
    }
    ///////////////////////////////////
    // Create the framegrabber object 
    // and start streaming data
    ///////////////////////////////////
    auto fg = std::make_shared<ifm3d::FrameGrabber>(device, pcic_port);
    fg->Start({ifm3d::buffer_id::XYZ});
    
    // Get a frame
    auto future = fg->WaitForFrame();
    if (future.wait_for(3s) != std::future_status::ready) {
        std::cerr << "Timeout waiting for camera!" << std::endl;
        return -1;
    }
    auto frame = future.get();

    ///////////////////////////////////
    // Get the data from the frame and
    // print out the format.
    ///////////////////////////////////
    ifm3d::Buffer xyz = frame->GetBuffer(ifm3d::buffer_id::XYZ);

    // Query the data format and channel.
    std::cout << "Number of channels: " << xyz.nchannels() << std::endl;
    std::cout << "Data format: " << pixel_format_to_string(xyz.dataFormat()) << std::endl;

    fg->Stop();
    return 0;
}