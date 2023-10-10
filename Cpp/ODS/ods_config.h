#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#ifdef USE_JSONSCHEMA
    #include <nlohmann/json-schema.hpp>
    #include <nlohmann/json.hpp> // nlohmann json needs to be included before any ifm3d include.
    
    #define IFM3D_JSON_NLOHMANN_COMPAT // enable the nlohmann json converter
    #include <ifm3d/common/json.hpp>

    #include <ifm3d/device/o3r.h>
    #include <ifm3d/device/err.h>
    class Validator {
    public:
        ifm3d::O3R::Ptr o3r;
        ifm3d::json o3r_schema;
        Validator(ifm3d::O3R::Ptr o3r_) : o3r(o3r_) {
            o3r_schema = o3r->GetSchema();
            try {
                validator.set_root_schema(nlohmann::json::parse(o3r_schema.dump(0)));
            }
            catch (const std::exception &e) {
                std::cerr << "Validation of schema failed: "
                        << e.what()
                        << std::endl;
            }
        }
        void ValidateJson(ifm3d::json config) {
            // This validation function will provide verbose
            // errors when the provided json configuration 
            // is wrong.
            try {
                validator.validate(nlohmann::json::parse(config.dump(0)));
                std::clog << "Successful JSON validation."  << std::endl;
            }
            catch (const std::exception &e) {
                std::cerr << "Validation failed: "
                        << e.what()
                        << std::endl;
            }
        }

    private:

        nlohmann::json_schema::json_validator validator{ nullptr, CheckJSONFormat };

        static void CheckJSONFormat(const std::string& format, const std::string& value) {
            // This is necessary because "format" is a keyword both used internally by the schema
            // validator and in the O3R schema.
            if (format == "ipv4") {
                std::clog << "IPV4 formatting";
                // if (!std::get<0>(ifm::eucco::network::normalizeIPv4Address(QString::fromStdString(value))))
                // {
                //     throw std::invalid_argument("unknown ip format");
                // }
            }
            else {
                throw std::logic_error("Don't know how to validate " + format);
            }
        }
    };

#else
    #include <ifm3d/device/o3r.h>
    #include <ifm3d/device/err.h>

    class Validator {
    public:
        ifm3d::O3R::Ptr o3r;

        Validator(ifm3d::O3R::Ptr o3r_) : o3r(o3r_) {
            std::clog << "JSON validation unavailable: missing dependency." << std::endl;
        }
        void ValidateJson(ifm3d::json config) {
            std::clog << "JSON validation unavailable." << std::endl;
        }
    };
#endif


using namespace ifm3d::literals;

class ODSConfig {
public:
    ifm3d::O3R::Ptr o3r;
    Validator val;

    ODSConfig(ifm3d::O3R::Ptr o3r_) : o3r(o3r_), val(o3r) {
    }

    void SetConfigFromFile(const std::string& config_path) {
        // Reading a configuration from file and setting it
        std::clog << "Reading configuration file at: " 
                  << config_path
                  << std::endl;
        std::ifstream config_file;
        config_file.exceptions(std::ifstream::failbit | std::ifstream::badbit);
        std::stringstream config_buffer;
        try {
            config_file.open(config_path);
            if (config_file.is_open()) {
                config_buffer << config_file.rdbuf();
            }
            SetConfigFromStr(config_buffer.str());
        }
        catch (const std::ifstream::failure& e) {
            std::cerr << "Caught exception while reading configuration file: " 
                      << e.what() 
                      << std::endl;
        }
        catch (...) {
            std::cerr << "Unknown error while reading configuration file."
                      << std::endl;
        }
    }

    void SetConfigFromStr(const std::string& config_str) {
        try {
            val.ValidateJson(ifm3d::json::parse(config_str));
            o3r->Set(ifm3d::json::parse(config_str));
            std::clog << "Successfully set the configuration." << std::endl;
        }
        catch (const std::exception &e) {
            std::cerr << "Caught exception while configuring: "
                      << e.what()
                      << std::endl;
        }
    }
};
