#include <cstdlib>
#include <iostream>
#include <fstream>
#include <ifm3d/device/o3r.h>
#include <ifm3d/fg.h>
using namespace ifm3d::literals;

class O3RDiagnostic {
public:
    ifm3d::O3R::Ptr o3r;
    ifm3d::FrameGrabber::Ptr fg;
    std::streambuf* consoleBuffer;
    bool log_to_file;
    std::ofstream logFile;
    ifm3d::json diagnostic = ifm3d::json::parse(R"({"id": "None", "message": "None"})");

    O3RDiagnostic(ifm3d::O3R::Ptr o3r_, bool log_to_file_ = false, const std::string& file_name_ = "") 
        : o3r(o3r_), 
          log_to_file(log_to_file_), 
          fg(std::make_shared<ifm3d::FrameGrabber>(o3r, 50009)),
          consoleBuffer(std::clog.rdbuf())
    {
        if (log_to_file){
            const std::string& log_file_name = (file_name_.empty()) ? "O3R_diagnostic.txt" : file_name_;
            if (log_to_file)
            {
                logFile.open(log_file_name, std::ios::app);  // Open the log file
                // Check if the file opened successfully
                if (!logFile.is_open())
                {
                    std::cerr << "Failed to open log file: " << log_file_name << std::endl;
                    return;
                }
                std::streambuf* fileBuffer = logFile.rdbuf();
                // Redirect std::clog to the log file
                std::clog.rdbuf(fileBuffer);
            }
        }
        std::clog.rdbuf(consoleBuffer);
    }

    ifm3d::json GetDiagnosticFiltered(ifm3d::json filter_mask_) {
        try {
            return o3r->GetDiagnosticFiltered(filter_mask_);
        } catch (...) {
            throw;
        }
    }

    void StartAsyncDiag() {
        fg->OnAsyncError([this](int id_, const std::string &message_) {
            this->AsyncDiagCallback_(id_, message_);
        });
        fg->Start({});
    }

    void StopAsyncDiag() {
        fg->Stop();
    }

    ~O3RDiagnostic() {
        // Stop the frame grabber if it's still running
        fg->Stop();

        // Restore the console output stream buffer
        std::clog.rdbuf(consoleBuffer);

        // Close the log file if it's open
        if (logFile.is_open()) {
            logFile.close();
        }
    }
private:
    void AsyncDiagCallback_(int id_, std::string message_) {
        diagnostic["id"] = id_;
        diagnostic["message"] = message_;
        std::clog << "\n//////////////////////////////////"
                  << std::endl;
        std::clog << "Id: " << diagnostic["id"]
                  << std::endl;
        std::clog << "Message: " << diagnostic["message"]
                  << std::endl;
    }
};
