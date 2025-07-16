#ifndef CONFIG_LOADER_HPP
#define CONFIG_LOADER_HPP

#include <fstream>
#include <ifm3d/common/json.hpp>
#include <iostream>
#include <stdexcept>

class ConfigLoader {
public:
  static ifm3d::json LoadConfig(const std::string &config_path) {
    std::ifstream file(config_path);
    if (!file.is_open()) {
      throw std::runtime_error("Failed to open config file: " + config_path);
    }

    ifm3d::json config;
    file >> config;
    file.close();

    std::cout << "Loaded configuration from: " << config_path << std::endl;
    return config;
  }
};

#endif // CONFIG_LOADER_HPP
