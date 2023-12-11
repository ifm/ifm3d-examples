/*
 * Copyright (C) 2018 ifm electronics, gmbh
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distribted on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

//
// ex-multi_camera_grabber.cpp
//
// Capture frames from multiple ifm 3D cameras which are configured to be triggered through software,
// and display the time stamp of the frame received.
// also measues the time taken to receive the set of frames.
//
// Prerequisites:
// *) Each ifm 3D camera should be configured to use "Process Interface" for trigger.
// *) You Should be able to ping each of the 3D camera from the PC on which this code executes.
// *) Incase your network uses a proxy, you will need to configure your system to bypass the proxy for the used IP's.
//

#include <iostream>
#include <memory>
#include <chrono>
#include <vector>
#include <ctime>
#include <iomanip>
#include <ifm3d/camera.h>
#include <ifm3d/fg.h>
#include <ifm3d/image.h>

namespace
{
    //CHANGE IP addreses to those of camera's avaialible!!!!
    const auto CAMERA0 = "192.168.0.70";
    const auto CAMERA1 = "192.168.0.71";
    const auto CAMERA2 = "192.168.0.72";

    //Add the IP of cameras to be used.
    const std::array<const std::string,3> camera_ips = {CAMERA0, CAMERA1, CAMERA2};

    //Utility function to format the timestamp
    std::string formatTimestamp(ifm3d::TimePointT timestamp)
    {
        std::time_t time = std::chrono::system_clock::to_time_t(
                    std::chrono::time_point_cast<std::chrono::system_clock::duration>(
                        timestamp));

        std::chrono::milliseconds milli = std::chrono::duration_cast<std::chrono::milliseconds>(
                    timestamp.time_since_epoch() - std::chrono::duration_cast<std::chrono::seconds>(
                        timestamp.time_since_epoch()));

        std::ostringstream s;
        s << std::put_time(std::localtime(&time), "%Y-%m-%d %H:%M:%S")
          << ":" << std::setw(3) << std::setfill('0') << milli.count();

        return s.str();
    }
}


int main(int argc, const char **argv)
{
    std::chrono::system_clock::time_point start, end;

    //vectors for the objects to be used.
    std::vector<ifm3d::Camera::Ptr> cameras;
    std::vector<ifm3d::FrameGrabber::Ptr> frame_grabbers;
    std::vector<ifm3d::ImageBuffer::Ptr> image_buffers;

    // Create ifm3d objects of Camera, ImageBuffer and FrameGrabber for each of the camera devices.
    for(auto camera_ip:camera_ips)
    {
        auto cam = ifm3d::Camera::MakeShared(camera_ip);
        cameras.push_back(cam);
        image_buffers.push_back(std::make_shared<ifm3d::ImageBuffer>());
        frame_grabbers.push_back(std::make_shared<ifm3d::FrameGrabber>(cam));

    }

    int count = 0;
    while (count++ < 10)
    {
        //for each of the camera device, software trigger is sent and wait for frame is done sequentially.
        start = std::chrono::system_clock::now();
        for(int index = 0; index<camera_ips.size();index++ )
        {
            auto frame_grabber = frame_grabbers.at(index);
            auto image_buffer = image_buffers.at(index);

            frame_grabber->SWTrigger();
            if (!frame_grabber->WaitForFrame(image_buffer.get(), 1000))
            {
                std::cerr << "Timeout waiting for camera("<<camera_ips[index]<<") !" << std::endl;
                return -1;
            }
            else {
                ifm3d::TimePointT timestamp = image_buffer->TimeStamp();
                std::cout << "got camera("<<camera_ips[index]<<") frame, timestamp"
                          << std::setw(2) << std::setfill('0')
                          << ": " << formatTimestamp(timestamp)
                          << std::endl;
            }

        }
        end = std::chrono::system_clock::now();
        std::chrono::duration<double, std::milli> duration_ms = (end - start);
        std::cout << "total get time in ms: " << duration_ms.count()<< std::endl;
    }

    return 0;
}
