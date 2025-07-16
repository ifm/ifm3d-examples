#include <chrono>
#include <ifm3d/common/logging/log.h>
#include <ifm3d/common/logging/log_writer.h>
#include <ifm3d/common/logging/logger.h>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
#include <memory>
#include <thread>

#include <spdlog/sinks/basic_file_sink.h>
#include <spdlog/sinks/stdout_color_sinks.h>
#include <spdlog/spdlog.h>

using namespace ifm3d::literals;

class LogWriterSpdLog : public ifm3d::LogWriter {
public:
  LogWriterSpdLog() {
    // create file logger
    auto file_sink =
        std::make_shared<spdlog::sinks::basic_file_sink_mt>("logger.txt", true);
    // create Console logger
    auto console_sink = std::make_shared<spdlog::sinks::stdout_color_sink_mt>();
    logger_ = std::make_shared<spdlog::logger>(
        "logger", spdlog::sinks_init_list({file_sink, console_sink}));
    this->logger_->set_level(spdlog::level::debug);
    spdlog::set_default_logger(logger_);
  }

  void Write(const ifm3d::LogEntry &entry) override {
    spdlog::level::level_enum spdlog_level;
    switch (entry.GetLogLevel()) {
    case ifm3d::LogLevel::Critical:
      spdlog_level = spdlog::level::critical;
      break;
    case ifm3d::LogLevel::Error:
      spdlog_level = spdlog::level::err;
      break;
    case ifm3d::LogLevel::Warning:
      spdlog_level = spdlog::level::warn;
      break;
    case ifm3d::LogLevel::Info:
      spdlog_level = spdlog::level::info;
      break;
    case ifm3d::LogLevel::Debug:
      spdlog_level = spdlog::level::debug;
      break;
    case ifm3d::LogLevel::Verbose:
      spdlog_level = spdlog::level::trace;
      break;
    default:
      spdlog_level = spdlog::level::off;
    }

    this->logger_->log(
        spdlog::source_loc(entry.GetFile(), entry.GetLine(), entry.GetFunc()),
        spdlog_level, entry.GetMessage());
  }

private:
  std::shared_ptr<spdlog::logger> logger_;
};

int main() {
  // create custom logger instance
  auto custom_logger = std::make_shared<LogWriterSpdLog>();

  // Redirect ifm3d logging to spdlog
  auto &logger = ifm3d::Logger::Get();
  logger.SetWriter(custom_logger);
  logger.SetLogLevel(ifm3d::LogLevel::Verbose);

  // Declare the device object (one object only, corresponding to the VPU)
  auto dev = std::make_shared<ifm3d::O3R>();
  LOG_INFO("Device creation done");

  // Declare the FrameGrabber
  // One FrameGrabber per camera head (define the port number).
  const auto FG_PCIC_PORT =
      dev->Get()["/ports/port2/data/pcicTCPPort"_json_pointer];
  auto fg = std::make_shared<ifm3d::FrameGrabber>(dev, FG_PCIC_PORT);

  LOG_DEBUG("Setting Schema");

  // Set Schema and start the grabber
  fg->Start({ifm3d::buffer_id::NORM_AMPLITUDE_IMAGE,
             ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE, ifm3d::buffer_id::XYZ,
             ifm3d::buffer_id::CONFIDENCE_IMAGE});

  // Use the framegrabber in streaming mode
  fg->OnNewFrame([&](ifm3d::Frame::Ptr frame) {
    auto distance_image = frame->GetBuffer(ifm3d::buffer_id::CONFIDENCE_IMAGE);
    LOG_INFO("Width: {}, Height: {}", distance_image.width(),
             distance_image.height());
  });

  std::this_thread::sleep_for(std::chrono::seconds(10));
  fg->Stop();

  return 0;
}
