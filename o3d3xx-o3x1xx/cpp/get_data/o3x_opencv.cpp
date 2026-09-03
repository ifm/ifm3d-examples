#include <ifm3d/device.h>
#include <ifm3d/fg.h>
#include <opencv2/opencv.hpp>

#include <atomic>
#include <chrono>
#include <ctime>
#include <iomanip>
#include <iostream>
#include <mutex>
#include <sstream>
#include <thread>

static cv::Mat render_jet(const cv::Mat &single_channel) {
  CV_Assert(single_channel.channels() == 1);
  int depth = single_channel.depth();
  CV_Assert(depth == CV_32F || depth == CV_64F || depth == CV_16U ||
            depth == CV_16S);

  cv::Mat f32;
  if (depth != CV_32F) {
    single_channel.convertTo(f32, CV_32F);
  } else {
    f32 = single_channel;
  }

  double minv, maxv;
  cv::minMaxLoc(f32, &minv, &maxv);
  double maxAbs = std::max(std::abs(minv), std::abs(maxv));
  if (maxAbs < 1e-12)
    maxAbs = 1.0;

  cv::Mat absf;
  cv::absdiff(f32, 0, absf);
  cv::Mat scaled8u;
  absf.convertTo(scaled8u, CV_8U, 255.0 / maxAbs);

  cv::Mat color;
  cv::applyColorMap(scaled8u, color, cv::COLORMAP_JET);
  return color; // CV_8UC3
}

// Convert an ifm3d::Buffer (float32 distance image) to a CV_32F cv::Mat by copy
static cv::Mat buffer_to_cv32f(const ifm3d::Buffer &buf) {
  const int rows = static_cast<int>(buf.height());
  const int cols = static_cast<int>(buf.width());

  cv::Mat out(rows, cols, CV_32F);
  for (int r = 0; r < rows; ++r) {
    float *dst = out.ptr<float>(r);
    for (int c = 0; c < cols; ++c) {
      dst[c] = buf.at<float>(r, c);
    }
  }
  return out;
}

int main() {
  // IP via env var IFM3D_IP or ifm3d default
  const char *IP = std::getenv("IFM3D_IP") ? std::getenv("IFM3D_IP")
                                           : ifm3d::DEFAULT_IP.c_str();
  std::clog << "Connecting to O3X at " << IP << std::endl;

  // Device and framegrabber
  auto device = ifm3d::Device::MakeShared(IP);
  auto fg = std::make_shared<ifm3d::FrameGrabber>(device);

  // Enable the free running mode.
  device->FromJSONStr(R"({"Apps":[{"TriggerMode":"1"}]})");

  // Request only the radial distance buffer
  fg->Start({ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE});

  // Shared state from callback to UI thread
  std::mutex mtx;
  ifm3d::Buffer latest_radial; // keep native buffer
  std::atomic<bool> has_frame{false};
  std::atomic<bool> running{true};

  // Register callback
  fg->OnNewFrame([&](ifm3d::Frame::Ptr frame) {
    try {
      auto dist = frame->GetBuffer(ifm3d::buffer_id::RADIAL_DISTANCE_IMAGE);
      std::lock_guard<std::mutex> lk(mtx);
      latest_radial = dist.clone(); // Buffer -> Buffer
      has_frame.store(true, std::memory_order_relaxed);
    } catch (const std::exception &e) {
      std::cerr << "Frame error: " << e.what() << std::endl;
    }
  });

  const std::string window_name = "O3X radial distance (ESC=exit, X=save)";
  cv::namedWindow(window_name, cv::WINDOW_NORMAL);

  // UI/render loop
  while (running.load(std::memory_order_relaxed)) {
    ifm3d::Buffer buf;
    {
      std::lock_guard<std::mutex> lk(mtx);
      if (has_frame.load(std::memory_order_relaxed)) {
        buf = latest_radial.clone();
      }
    }

    if (has_frame.load(std::memory_order_relaxed) && buf.width() > 0 &&
        buf.height() > 0) {
      // Convert to cv::Mat and render
      cv::Mat radial32f = buffer_to_cv32f(buf);
      cv::Mat color = render_jet(radial32f);

      // Add a small title strip
      int thumbnail_h = 30;
      cv::Mat title(thumbnail_h, color.cols, CV_8UC3, cv::Scalar(0, 0, 0));
      cv::putText(title, "radial distance", {5, thumbnail_h - 10},
                  cv::FONT_HERSHEY_SIMPLEX, 0.6, cv::Scalar(255, 255, 255), 1,
                  cv::LINE_AA);
      cv::Mat labeled;
      cv::vconcat(title, color, labeled);
      cv::copyMakeBorder(labeled, labeled, 2, 2, 2, 2, cv::BORDER_CONSTANT,
                         cv::Scalar(0, 0, 0));

      cv::imshow(window_name, labeled);

      int key = cv::waitKey(1);
      if (key == 27) {
        running.store(false, std::memory_order_relaxed);
      } else if (key == 'x' || key == 'X') {
        auto tt = std::time(nullptr);
        std::tm tm{};
#if defined(_WIN32)
        localtime_s(&tm, &tt);
#else
        localtime_r(&tt, &tm);
#endif
        std::ostringstream oss;
        oss << "o3x_radial_" << std::put_time(&tm, "%Y%m%d-%H%M%S") << ".png";
        cv::imwrite(oss.str(), labeled);
        std::cout << "Saved frame to " << oss.str() << std::endl;
      }
    } else {
      std::this_thread::sleep_for(std::chrono::milliseconds(5));
    }
  }

  fg->Stop();
  cv::destroyAllWindows();
  return 0;
}
