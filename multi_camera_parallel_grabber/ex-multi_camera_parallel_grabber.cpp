/*
 * Copyright (C) 2019 ifm electronic, gmbh
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

//
// ex-multi_camera_parallel_grabber.cpp
//
// setup : refer README.md file
//
// Prerequisites:
// *) one ifm 3D camera should be configured to use "Process Interface" for trigger.
// *) All other camera must be in hardware trigger mode
//


#include <iostream>
#include <memory>
#include <chrono>
#include <vector>
#include <thread>
#include <atomic>
#include <mutex>
#include <signal.h>
#include <array>
#include <tuple>
#include <iomanip>
#include <ifm3d/camera.h>
#include <ifm3d/fg.h>
#include <ifm3d/image.h>
#include <opencv2/core/core.hpp>
#include <opencv2/imgcodecs.hpp>
#include <opencv2/highgui/highgui.hpp>

namespace
{
  // enum for all the trigger types supported by o3d3xx device
  enum class trigger_mode : int { FREE_RUN = 1, SW = 2, POSITIVE_EDGE = 3, NEGATIVE_EDGE = 4, POSITIVE_N_NEGATIVE = 5 };

  //flag for stoping the application
  std::atomic<bool> start(true);

  //Add the IP of cameras to be used for the complete stystem. Address at 0th location must be of camera with software trigger
  /* to add device add device address at second last position in the camera_ips vector, increase NUMBER_OF_DEVICES too */
  constexpr  auto NUMBER_OF_DEVICES = 3;
  const  std::array<std::string, NUMBER_OF_DEVICES> camera_ips = { "192.168.0.70", "192.168.0.71","192.168.0.72"};

  auto j_conf = json::parse(R"(
        {
          "ifm3d":
          {
            "Device":
            {
              "ActiveApplication": "1"
            },
            "Apps":
            [
              {
                "Index": "1",
                "TriggerMode":"2",
                "LogicGraph": "{\"IOMap\": {\"OUT1\": \"RFT\",\"OUT2\": \"AQUFIN\"},\"blocks\": {\"B00001\": {\"pos\": {\"x\": 200,\"y\": 200},\"properties\": {},\"type\": \"PIN_EVENT_IMAGE_ACQUISITION_FINISHED\"},\"B00002\": {\"pos\": {\"x\": 200,\"y\": 75},\"properties\": {},\"type\": \"PIN_EVENT_READY_FOR_TRIGGER\"},\"B00003\": {\"pos\": {\"x\": 600,\"y\": 75},\"properties\": {\"pulse_duration\": 0},\"type\": \"DIGITAL_OUT1\"},\"B00005\": {\"pos\": {\"x\": 600,\"y\": 200},\"properties\": {\"pulse_duration\": 0},\"type\": \"DIGITAL_OUT2\"}},\"connectors\": {\"C00000\": {\"dst\": \"B00003\",\"dstEP\": 0,\"src\": \"B00002\",\"srcEP\": 0},\"C00001\": {\"dst\": \"B00005\",\"dstEP\": 0,\"src\": \"B00001\",\"srcEP\": 0}}}",
                "Imager":
                {
                    "ExposureTime": "1000",
                    "Type":"under5m_moderate",
                    "FrameRate":"20"
                }
              }
            ]
          }
        }
    )");

  //for configuration of required trigger on camera
  void configuration(ifm3d::Camera* camera, trigger_mode type)
  {
    auto application_id = camera->ActiveApplication();
    j_conf["ifm3d"]["Device"]["ActiveApplication"] = std::to_string(application_id);
    j_conf["ifm3d"]["Apps"][0]["Index"] = std::to_string(application_id);
    j_conf["ifm3d"]["Apps"][0]["TriggerMode"] = std::to_string((int)type);

    camera->FromJSON(j_conf);
  }
  // class to encapsulate all the camera related resource and grabbing images
  struct  CameraObject
  {
    using Ptr = std::shared_ptr<CameraObject>;
    using Callback = std::function<void(ifm3d::ImageBuffer* image_buffer, bool in_time)>;

    CameraObject(std::string ip_address, trigger_mode type)
    {
      //initialize all the objects and configure the device with trigger type
      //connecting to camer
      camera = ifm3d::Camera::MakeShared(ip_address);
      frame_grabber = std::make_unique<ifm3d::FrameGrabber>(camera, ifm3d::IMG_AMP);
      image_buffer = std::make_unique<ifm3d::ImageBuffer>();
      std::cout << "Connected to the device with IP Address " << ip_address << std::endl;

      // configure the CAMERA acoording to the type
      configuration(camera.get(), type);
    }

    ifm3d::Camera::Ptr camera;
    std::unique_ptr<ifm3d::ImageBuffer> image_buffer;
    std::unique_ptr<ifm3d::FrameGrabber> frame_grabber;
    std::mutex mutex;

    void grabimage(Callback callback)
    {
      while (start)
      {
        std::this_thread::sleep_for(std::chrono::duration<int, std::milli>(1));
        {
          std::lock_guard<std::mutex> lock(mutex);
          const bool in_time = frame_grabber->WaitForFrame(image_buffer.get(), 10000);
          callback(image_buffer.get(), in_time);
        }
      }
    }
  };
}; //end namespcase

int main(int argc, const char **argv)
{

  std::cout << "--------------IFM3D Multi Threaded Grabber Example-------------------- " << std::endl;
  std::cout << std::endl << "CLOSE APPLICATION BY PRESSING CNTRL+C" << std::endl << std::endl << std::endl;

  // Worker threads for each camera.
  std::vector<std::thread> workers;
  std::array<std::tuple<CameraObject::Ptr, CameraObject::Callback>, NUMBER_OF_DEVICES> camera_object_list;

  // call back buffer for threads.user can write algorithms for each camera data
  // e.g. we increase the brigthness of each image by scaling pixel values by 100

  auto buf_callback =
    [&](auto image_buffer, bool in_time) -> void
  {
    if (in_time)
    {
      //Scaling to higer value to make image looks brighter
      image_buffer->AmplitudeImage() *= 100;
    }
    else
    {
      std::cout << "Timeout occured" << std::endl;
    }
  };

  // this trigger the first camera and call buffer_callback
  auto trig_callback =
    [&](auto image_buffer, bool in_time) -> void
  {
    // Trigger the next frame
    std::get<0>(camera_object_list[0])->frame_grabber->SWTrigger();
    // execute the regular callback
    buf_callback(image_buffer, in_time);

  };

  //system setup
  // first device will have Software trigger and all other will have hardware trigger.
  // The last device will trigger the first device hence a different trigger_call back for last device.
  // set the first device for SW trigger
  camera_object_list[0] = std::make_tuple(std::make_shared<CameraObject>(camera_ips[0], trigger_mode::SW), buf_callback);

  // all the devices after 1st Device must have hardware trigger.
  for (auto i = 1; i < NUMBER_OF_DEVICES - 1; ++i)
  {
    camera_object_list[i] = std::make_tuple(std::make_shared<CameraObject>(camera_ips[i], trigger_mode::POSITIVE_EDGE), buf_callback);
  }
  // last device setuped to call the trigger_callback.
  camera_object_list[NUMBER_OF_DEVICES- 1] = std::make_tuple(std::make_shared<CameraObject>(camera_ips[NUMBER_OF_DEVICES - 1], trigger_mode::POSITIVE_EDGE), trig_callback);

  // Starting the thread for each camera for grabbing data and calling respective callback function
  for (const auto &elem : camera_object_list)
  {
    workers.push_back(std::thread(std::bind(&CameraObject::grabimage, std::get<0>(elem), std::get<1>(elem))));
  }

  // Kickstart the loop by giving first camera a SW trigger
  std::get<0>(camera_object_list[0])->frame_grabber->SWTrigger();

  //this delay provides the initial setuptime for all the devices
  std::this_thread::sleep_for(std::chrono::milliseconds(10));

  // Function where all the data from camera is available for display
  auto display_all_images =
    [](decltype(camera_object_list) &camera_object_list)
  {
    cv::Mat all_images;
    cv::Mat image;
    cv::Mat last_image;
    int index = 0;
    while (start)
    {
      index = 0;
      for (const auto &camera_object : camera_object_list)
      {
        {
          std::lock_guard<std::mutex> lock(std::get<0>(camera_object)->mutex);
          image = std::get<0>(camera_object)->image_buffer->AmplitudeImage();
        }
        if (index != 0)
        {
          cv::hconcat(image, last_image, all_images);
          last_image = all_images;
        }
        else
        {
          all_images = image;
          last_image = all_images;
        }
        index++;
      }
      cv::imshow("Display side by side", all_images);
      cv::waitKey(2);
    }
  };

  workers.push_back(
    std::thread(
      std::bind(display_all_images, camera_object_list))
  );

  auto closeApplication = [](int signal)
  {
    start = false;
  };

  signal(SIGINT, closeApplication);

  //waiting for all threads to complete
  for (auto &worker : workers)
  {
    if (worker.joinable())
    {
      worker.join();
    }
  }
  return 0;
}
