#include <cstdlib>
#include <fstream>
#include <functional>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
#include <iostream>
using namespace ifm3d::literals;

class O3RDiagnostic {
public:
  O3RDiagnostic(ifm3d::O3R::Ptr o3r, bool log_to_file = false,
                const std::string &file_name_ = "")
      : o3r_(o3r), log_to_file_(log_to_file),
        fg_(std::make_shared<ifm3d::FrameGrabber>(o3r_, 50009)),
        consoleBuffer_(std::clog.rdbuf()) {
    if (log_to_file_) {
      const std::string &log_file_name =
          (file_name_.empty()) ? "O3R_diagnostic.txt" : file_name_;
      if (log_to_file_) {
        logFile_.open(log_file_name, std::ios::app); // Open the log file
        // Check if the file opened successfully
        if (!logFile_.is_open()) {
          std::cerr << "Failed to open log file: " << log_file_name
                    << std::endl;
          return;
        }
        std::streambuf *fileBuffer = logFile_.rdbuf();
        // Redirect std::clog to the log file
        std::clog.rdbuf(fileBuffer);
      }
    }
    std::clog.rdbuf(consoleBuffer_);
  }

  ifm3d::json GetDiagnosticFiltered(ifm3d::json filter_mask_) {
    return o3r_->GetDiagnosticFiltered(filter_mask_);
  }

  void StartAsyncDiag() {
    fg_->OnAsyncError([this](int id_, const std::string &message_) {
      this->AsyncDiagCallback_(id_, message_);
    });
    fg_->Start({});
  }

  void StartAsyncDiag(std::function<void(int, const std::string&)> callback) {
    fg_->OnAsyncError(callback);
    fg_->Start({});
  }

  void StopAsyncDiag() { fg_->Stop(); }

  ~O3RDiagnostic() {
    // Stop the frame grabber if it's still running
    fg_->Stop();

    // Restore the console output stream buffer
    std::clog.rdbuf(consoleBuffer_);

    // Close the log file if it's open
    if (logFile_.is_open()) {
      logFile_.close();
    }
  }

private:
  ifm3d::O3R::Ptr o3r_;
  ifm3d::FrameGrabber::Ptr fg_;
  std::streambuf *consoleBuffer_;
  bool log_to_file_;
  std::ofstream logFile_;
  ifm3d::json diagnostic_ =
      ifm3d::json::parse(R"({"id": "None", "message": "None"})");
  
  void AsyncDiagCallback_(int id_, std::string message_) {
    diagnostic_["id"] = id_;
    diagnostic_["message"] = message_;
    std::clog << "\n//////////////////////////////////" << std::endl;
    std::clog << "Id: " << diagnostic_["id"] << std::endl;
    std::clog << "Message: " << diagnostic_["message"] << std::endl;
  }
};
