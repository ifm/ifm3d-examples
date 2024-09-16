/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */

// This example shows how to unpack diagnostic
// data from the O3D camera.
// The diagnostic data provides important 
// information about the camera's internal state,
// such as the temperature.
#include <atomic>
#include <chrono>
#include <iostream>
#include <string>
#include <thread>
#include <cstdint>
#include <cstring>
#include <tuple>
#include <vector>
#include <ifm3d/fg.h>
#include <ifm3d/device/o3d.h>

using namespace std::chrono_literals;
using namespace ifm3d::literals;

std::tuple<int32_t, int32_t, int32_t, int32_t, uint32_t, uint32_t> unpackData(ifm3d::Buffer_<std::uint8_t>& data) {
    int32_t i1, i2, i3, i4;
    uint32_t u1, u2;

    // Assuming data is at least 24 bytes: 4 ints (4*4 bytes) + 2 uints (2*4 bytes)
    std::memcpy(&i1, data.ptr(0), sizeof(i1));
    std::memcpy(&i2, data.ptr(0) + 4, sizeof(i2));
    std::memcpy(&i3, data.ptr(0) + 8, sizeof(i3));
    std::memcpy(&i4, data.ptr(0) + 12, sizeof(i4));
    std::memcpy(&u1, data.ptr(0) + 16, sizeof(u1));
    std::memcpy(&u2, data.ptr(0) + 20, sizeof(u2));

    return std::make_tuple(i1, i2, i3, i4, u1, u2);
}

int main() {
    //////////////////////////
    // Declare the O3D objects
    // and start the data stream.
    //////////////////////////
    // Get the IP from the environment if defined
    const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP") : ifm3d::DEFAULT_IP.c_str();
    std::clog << "IP: " << IP << std::endl;
    auto o3d = std::make_shared<ifm3d::O3D>(IP);
    auto fg = std::make_shared<ifm3d::FrameGrabber>(o3d, std::stoi(o3d->DeviceParameter("PcicTcpPort")));
    
    // Start the grabber
    fg->Start({ifm3d::buffer_id::DIAGNOSTIC});
    // Grace period before trying to get a frame
    std::this_thread::sleep_for(std::chrono::seconds(5));
    
    //////////////////////////
    // Get a frame
    //////////////////////////
    auto future = fg->WaitForFrame();
    if (future.wait_for(3s) != std::future_status::ready) {
        std::cerr << "Timeout waiting for camera!" << std::endl;
        return -1;
    }
    auto frame = future.get();

    //////////////////////////
    // Get the data
    //////////////////////////
    auto diagnostic_buffer = frame->GetBuffer(ifm3d::buffer_id::DIAGNOSTIC);
    // The diagnostic data is of format unsigned int8
    ifm3d::Buffer_<std::uint8_t> diag = diagnostic_buffer;
    auto unpacked_diagnostic = unpackData(diag);
    std::cout << "Illumination temperature (0.1 °C), invalid = 32767: "
              << std::get<0>(unpacked_diagnostic)
              << std::endl;
    std::cout << "Frontend temperature 1 (0.1 °C), invalid = 32767: "
              << std::get<1>(unpacked_diagnostic)
              << std::endl;
    std::cout << "Frontend temperature 2 (0.1 °C), invalid = 32767: "
              << std::get<2>(unpacked_diagnostic)
              << std::endl;              
    std::cout << "i.mx6 Temperature (0.1 °C), invalid = 32767: "
              << std::get<3>(unpacked_diagnostic)
              << std::endl;
    std::cout << "Frame duration: "
              << std::get<4>(unpacked_diagnostic)
              << std::endl;
    std::cout << "Framerate: "
              << std::get<5>(unpacked_diagnostic)
              << std::endl;                            
    return 0;
}