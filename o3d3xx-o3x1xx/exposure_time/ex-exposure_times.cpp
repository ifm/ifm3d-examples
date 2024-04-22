/*
 * Copyright (C) 2016 Love Park Robotics, LLC
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
// ex-exposure_times.cpp
//
//  Shows how to change imager exposure times on the fly while streaming in
//  pixel data and validating the setting of the exposure times registered to
//  the frame data.
//

#include <cstdint>
#include <iostream>
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include <ifm3d/device/device.h>
#include <ifm3d/device/legacy_device.h>
#include <ifm3d/fg.h>

int main(int argc, const char **argv)
{
  // example configuration for the camera we will use for exemplary purpose
  // we will use a double exposure imager.
  std::string json = R"(
        {
          "ifm3d":
          {
            "Device":
            {
              "ActiveApplication": "2"
            },
            "Apps":
            [
              {
                "TriggerMode": "1",
                "Index": "2",
                "Imager":
                {
                    "ExposureTime": "5000",
                    "ExposureTimeList": "125;5000",
                    "ExposureTimeRatio": "40",
                    "Type":"under5m_moderate"
                }
              }
           ]
          }
        }
      )";

  ifm3d::json config;
  // instantiate the camera and set the configuration
  auto cam = ifm3d::Device::MakeShared();
  auto l_cam = std::dynamic_pointer_cast<ifm3d::LegacyDevice>(cam);


  // instantiate our framegrabber and be sure to explicitly tell it to
  // stream back the exposure times registered to the frame data
  ifm3d::FrameGrabber::Ptr fg = std::make_shared<ifm3d::FrameGrabber>(cam);
  fg->Start({ifm3d::buffer_id::EXPOSURE_TIME, ifm3d::buffer_id::ILLUMINATION_TEMP});

  // a vector to hold the exposure times (we will just print them to the
  // screen)
  std::vector<std::uint32_t> exposure_times;

  // a map use to modulate the `ExposureTime` and `ExposureTimeRatio`
  // on-the-fly. We seed it with data consistent with our config above
  std::unordered_map<std::string, std::string> params =
    {
      {"imager_001/ExposureTime", "5000"},
      {"imager_001/ExposureTimeRatio", "40"}
    };

  // create a session with the camera so we can modulate the exposure times
  l_cam->RequestSession();

  //
  // NOTE: I'm going to do nothing with this here. However, in a *real*
  // application, you will have to send `Heartbeats` at least every `hb_secs`
  // seconds to the camera. The best technique for doing that is left as an
  // exercise for the reader.
  int hb_secs = l_cam->Heartbeat(300);

  // now we start looping over the image data, every 20 frames, we will
  // change the exposure times, after 100 frames we will exit.
  int i = 0;
  while (true)
    {
      auto frame = fg->WaitForFrame();
      if (frame.wait_for(std::chrono::milliseconds(1000)) != std::future_status::ready)
        {
          std::cerr << "Timeout waiting for camera!" << std::endl;
          continue;
        }

      // get the exposure times registered to the frame data
      auto exp_times = frame.get()->GetBuffer(ifm3d::buffer_id::EXPOSURE_TIME);
      auto illu_temp = l_cam->DeviceParameter("TemperatureIllu");
      for (const uint16_t time : ifm3d::IteratorAdapter<uint16_t>(exp_times))
      {
          exposure_times.push_back(time);
      }

      i++;
      if (i % 20 == 0)
        {
          std::cout << "\nFrameCount: " << i << std::endl;
          std::cout << "TemperatureIllu: " << illu_temp << " oC" << std::endl;
          std::cout << "Exposure times: " << exposure_times[0] << " : ";
          std::cout << exposure_times[2] << " uS"  << std::endl;

          std::cout << "Setting long exposure time to: ";
          if (exposure_times.at(2) == 5000)
            {
              std::cout << "10000" << std::endl;
                params["imager_001/ExposureTime"] = "10000";
            }
          else
            {
              std::cout << "5000" << std::endl;
              params["imager_001/ExposureTime"] = "5000";
            }

          l_cam->SetTemporaryApplicationParameters(params);
        }
        exposure_times.clear();

        if (i == 100)
        {
          l_cam->CancelSession();
          break;
        }

    }

  //
  // In a long-running program, you will need to take care to
  // clean up your session if necessary. Here we don't worry about it because
  // the camera dtor will do that for us.
  //
  std::cout << "\nExposure time read/write example done\n";
  return 0;
}
