/*
 * Copyright 2024-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
// This code example showcases how to retrieve data 
// continuously using a callback function.
// This example can be used for both the O3D and 
// the O3X cameras.

#include <chrono>
#include <cstdint>
#include <iostream>
#include <string>
#include <thread>
#include <ifm3d/common/json_impl.hpp>
#include <ifm3d/device/err.h>
#include <ifm3d/device.h>
#include <ifm3d/fg.h>

using namespace std::chrono_literals;
using namespace ifm3d::literals;

void Callback(ifm3d::Frame::Ptr frame) {
    // Get every image from the frame
    // and display a sample.
    std::cout << "Sample data from the frame (taken at pixel [50, 50] for each image): " << std::endl;

    // Refer to the get_data_format to find out 
    // the format for each image type.
    auto conf = frame->GetBuffer(ifm3d::buffer_id::CONFIDENCE_IMAGE);
    // The confidence image is of format unsigned int8
    std::cout << "Conf: " << std::to_string(conf.at<uint8_t>(50, 50)) << std::endl;

    auto dist = frame->GetBuffer(ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE);
    // The distance image is of format float 32
    std::cout << "Dist: " << std::to_string(dist.at<float>(50, 50)) << std::endl;


    auto noise = frame ->GetBuffer(ifm3d::buffer_id::RADIAL_DISTANCE_NOISE);
    // The noise image format is unsigned int16
    std::cout << "Noise: " << noise.at<std::uint16_t>(50,50) << std::endl;
    
    auto xyz = frame->GetBuffer(ifm3d::buffer_id::XYZ);
    // The XYZ image has three channels and its format is float
    auto xyz_ptr =  xyz.ptr<float>(50, 50);
    std::cout << "X: " << xyz_ptr[0] << std::endl;
    std::cout << "Y: " << xyz_ptr[1] << std::endl;
    std::cout << "Z: " << xyz_ptr[2] << std::endl;
}

int main() {
    // Get the IP from the environment if defined
    const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP") : ifm3d::DEFAULT_IP.c_str();
    std::clog << "IP: " << IP << std::endl;
    
    //////////////////////////
    // Declare the objects
    //////////////////////////
    // Declare the device object
    auto device = ifm3d::Device::MakeShared(IP);

    auto fg = std::make_shared<ifm3d::FrameGrabber>(device);

    //////////////////////////
    // Start the framegrabber
    // and register the callback
    //////////////////////////
    // Set Schema and start the grabber.
    // Here we are requesting all the most common
    // types of buffers that are available
    // for the two cameras.
    // Note that we are not requesting the 
    // amplitude image as it comes in two 
    // different buffers for the two cameras.
    fg->Start({ifm3d::buffer_id::CONFIDENCE_IMAGE,
                ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE, 
                ifm3d::buffer_id::RADIAL_DISTANCE_NOISE,
                ifm3d::buffer_id::XYZ});

    // Register callback function
    fg->OnNewFrame(&Callback);

    // This sleep is to prevent the program from before the
    // callback has time to execute.
    std::this_thread::sleep_for(5s);
    fg->Stop();

    return 0;
}