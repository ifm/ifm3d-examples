/*
 * Copyright 2025-present ifm electronic, gmbh
 * SPDX-License-Identifier: Apache-2.0
 */
#include <chrono>
#include <ifm3d/deserialize/struct_o3r_ods_extrinsic_calibration_correction_v1.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_info_v1.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_occupancy_grid_v1.hpp>
#include <ifm3d/deserialize/struct_o3r_ods_polar_occupancy_grid_v1.hpp>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <optional>
#include <queue>
#include <stdexcept>
#include <thread>

using namespace ifm3d::literals;

class ODSStream {
public:
  ODSStream(ifm3d::O3R::Ptr o3r_, const std::string &app_name_,
            ifm3d::FrameGrabber::BufferList buffer_ids_, int timeout_,
            int queue_size_ = 5)
      : o3r(o3r_), app_name(app_name_), buffer_ids(buffer_ids_),
        timeout(timeout_), queue_size(queue_size_) {
    auto FG_PCIC_PORT = o3r->Port(app_name).pcic_port;
    fg = std::make_shared<ifm3d::FrameGrabber>(o3r, FG_PCIC_PORT);
  }

  void StartODSStream() {
    std::clog << "Starting data stream" << std::endl;
    fg->Start(buffer_ids);
    fg->OnNewFrame([this](auto frame) { AddFrame(frame); });
  }

  void StopODSStream() {
    std::clog << "Stopping data stream" << std::endl;
    fg->Stop();
  }

  std::optional<ifm3d::ODSInfoV1> GetZones() {
    return GetFromQueue<ifm3d::ODSInfoV1>(zones_queue, timeout);
  }
  std::optional<ifm3d::ODSOccupancyGridV1> GetOccGrid() {
    return GetFromQueue<ifm3d::ODSOccupancyGridV1>(occ_grid_queue, timeout);
  }
  std::optional<ifm3d::ODSPolarOccupancyGridV1> GetPolarOccGrid() {
    return GetFromQueue<ifm3d::ODSPolarOccupancyGridV1>(polar_occ_grid_queue,
                                                        timeout);
  }
  std::optional<ifm3d::ODSExtrinsicCalibrationCorrectionV1>
  GetExtrinsicCalibrationCorrection() {
    return GetFromQueue<ifm3d::ODSExtrinsicCalibrationCorrectionV1>(
        extrinsic_calibration_correction_queue, timeout);
  }

private:
  template <typename T>
  std::optional<T> GetFromQueue(std::queue<ifm3d::Buffer> &queue,
                                int timeout_ms) {
    auto start = std::chrono::steady_clock::now();

    while (std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now() - start)
               .count() <= timeout_ms) {
      if (!queue.empty()) {
        auto data = T::Deserialize(queue.front());
        queue.pop();
        return data;
      }
      std::this_thread::sleep_for(
          std::chrono::milliseconds(1)); // Prevent CPU overuse
    }
    std::clog << "Timeout waiting for data" << std::endl; // Log the timeout
    return std::nullopt; // Return nullopt instead of throwing an exception
  }

  void AddFrame(ifm3d::Frame::Ptr frame) {
    AddToQueue(frame, ifm3d::buffer_id::O3R_ODS_INFO, zones_queue);
    AddToQueue(frame, ifm3d::buffer_id::O3R_ODS_OCCUPANCY_GRID, occ_grid_queue);
    AddToQueue(frame, ifm3d::buffer_id::O3R_ODS_POLAR_OCC_GRID,
               polar_occ_grid_queue);
    AddToQueue(frame,
               ifm3d::buffer_id::O3R_ODS_EXTRINSIC_CALIBRATION_CORRECTION,
               extrinsic_calibration_correction_queue);
  }

  void AddToQueue(ifm3d::Frame::Ptr frame, ifm3d::buffer_id id,
                  std::queue<ifm3d::Buffer> &queue) {
    if (frame->HasBuffer(id)) {
      if (queue.size() > queue_size)
        queue.pop();
      queue.push(frame->GetBuffer(id));
    }
  }

  ifm3d::O3R::Ptr o3r;
  std::string app_name;
  ifm3d::FrameGrabber::Ptr fg;
  ifm3d::FrameGrabber::BufferList buffer_ids;
  int timeout;
  int queue_size;

  std::queue<ifm3d::Buffer> zones_queue;
  std::queue<ifm3d::Buffer> occ_grid_queue;
  std::queue<ifm3d::Buffer> polar_occ_grid_queue;
  std::queue<ifm3d::Buffer> extrinsic_calibration_correction_queue;
};
