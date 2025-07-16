#include <fstream>
#include <ifm3d/device/err.h>
#include <ifm3d/device/o3r.h>
#include <iostream>
#include <stdexcept>
#include <string>

using namespace ifm3d;
int main() {
  try {
    const std::string IP_ADDRESS = "192.168.0.69";
    auto o3r = std::make_shared<ifm3d::O3R>(IP_ADDRESS);
    // Access the SealedBox API
    auto sealed_box = o3r->SealedBox();

    // Set new password
    const std::string password = "Colloportus"; // Example password
    sealed_box->SetPassword(password);
    std::cout << "Password set successfully" << std::endl;

    // Read SSH public key from file
    const std::string key_path =
        "/home/ifm/.ssh/id_o3r.pub"; // change to your key path
    std::ifstream key_file(key_path);
    if (!key_file.is_open()) {
      std::cerr << "Failed to open SSH public key file: " << key_path
                << std::endl;
      return -1;
    }
    std::stringstream buffer;
    buffer << key_file.rdbuf();
    std::string ssh_pub_key = buffer.str();
    key_file.close();

    ifm3d::json configuration = {
        {"device", {{"network", {{"authorized_keys", ssh_pub_key}}}}}};
    // Seal the configuration

    sealed_box->Set(password, configuration);

    std::cout << "Configuration sealed successfully" << std::endl;

    // Change the password
    const std::string new_password = "ProtegoMaxima2025"; // Example password
    sealed_box->SetPassword(new_password, password);
    std::cout << "Password changed successfully" << std::endl;

    // Remove the password

    sealed_box->RemovePassword(new_password);
    std::cout << "Password removed successfully" << std::endl;

  } catch (const ifm3d::Error &err) {
    std::cerr << "Error setting password: " << err.what() << std::endl;
    return -1;
  }
}
