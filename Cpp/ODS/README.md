# How to use these examples

## Pre-requisites

- The [ifm3d library >= v1.2.6](https://api.ifm3d.com/stable/content/installation_instructions/install_binary_package_index.html),
- Optional: 
    - The [`json-schema-validator`](https://github.com/pboettch/json-schema-validator) library, which depends on [`nlohmann-json` >= 3.8.x](https://github.com/nlohmann/json). We use this library to validate configurations before attempting to set them. The `json-schema-validator` library provides a more verbose error handling than ifm3d, which allows to identify precisely where the error is in the provided configuration.