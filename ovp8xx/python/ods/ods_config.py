#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
# %%
import json
import logging
import pathlib

from jsonschema import exceptions as json_exceptions
from jsonschema import validate

from ifm3dpy.device import Error as ifm3dpy_error
from ifm3dpy.device import O3R

logging.basicConfig(
    format="%(asctime)s:%(filename)-10s:%(levelname)-8s:%(message)s",
    datefmt="%y-%m-%d %H:%M:%S",
    level=logging.DEBUG
)
logger = logging.getLogger(__name__)


def validate_json(schema: dict, config: dict) -> dict:
    """
    This function can be used to validate
    a configuration before setting it.
    Note that ifm3dpy.device.O3R.set() will validate the
    requested configuration, but using the jsonschema.validate
    function will provide a more verbose validation.

    :param config: the configuration to validate
    :raises ValidationError: if the validation fails
    """
    try:
        logger.info(f"Validating configuration: {config}")
        validate(config, schema)
    except json_exceptions.ValidationError as err:
        logger.exception("Error while validating the json schema")
        raise err
    except json_exceptions.SchemaError as err:
        logger.exception("Incorrect json schema")
        raise err
    return (config)


def load_config_from_file(config_file: pathlib.Path) -> dict:
    """
    Configure the device from a configuration file.
    The provided configuration is validated using the schema validator.

    :param config_file: path to the configuration file
    """
    try:
        logger.info(f"Loading configuration from file {config_file}")
        with open(pathlib.Path(__file__).parent/config_file, "r") as f:
            config = json.load(f)
        return config
    except OSError as err:
        logger.exception("Error while reading configuration file")
        raise err


# %%
if __name__ == "__main__":
    # Example on how to use the above boilerplate.
    # Make sure you change the IP address for your specific setup.
    IP = "192.168.0.69"  # default
    o3r = O3R(IP)
    #############################################
    # Examples on getting configurations snippets
    #############################################
    logger.info(
        "Example: Getting various components of the VPU configuration...")
    for config_path_list in [
        [],  # Get the full configuration.
        # Get a subset of the configuration using JSON pointer
        ["/device/swVersion/firmware"],
        [  # Get multiple subsets of the configuration using JSON pointer
            "/device/swVersion/firmware",
            "/device/status",
            "/ports/port0/info",
        ],
    ]:
        config_snippet = o3r.get(config_path_list)
        logger.info(f"o3r.get({config_path_list}) -> {config_snippet}")

    # %%
    # ... if a key is unavailable, the resulting snippet will not have that key
    logger.info(
        "Demonstrating the unpacking of config retrieved from the VPU using a questionable JSON pointer...")
    config_snippet = o3r.get(["/ports/port5/info"])
    if (config_snippet["ports"] is not None):
        if ("port5" in config_snippet["ports"]):
            logger.info("port5 is present...")  # {'ports': {'port5': {...} }}
        else:
            logger.info("port5 is not present...")  # {'ports': {'port5':{}}}}
    else:
        # {'ports': None}
        logger.info(
            "port5 config unavailable... check diagnostics dump for possible explanation...")

    #####################################
    # Examples on setting configurations
    #####################################
    logger.info(
        "Example: Setting various components of the VPU configuration...")
    # Using the VPU schema is optional but can be useful for pinpointing why a given config snippet would fail to load onto the VPU
    schema = o3r.get_schema()

    invalid_snippet = {"device": {"info": {"description": 0}}}
    try:  # This will throw an exception
        validate_json(schema, invalid_snippet)
    # Failing silently to continue through the examples
        o3r.set(invalid_snippet)
    except json_exceptions.ValidationError:
        pass

    # This snippet is expected to be valid
    config_snippet = {"device": {
        "info": {"description": "I will use this O3R to change the world"}}}
    validate_json(schema, config_snippet)
    o3r.set(config_snippet)
    # In production, all possible exceptions must be considered but we will not worry about that here.

    # Set two configuration fragments at the same time. This schema will not be valid if the specified port is not plugged in and recognized by the VPU
    config_snippet = {
        "device": {"info": {"name": "my_favorite_o3r"}},
        "ports": {"port0": {"info": {"name": "my_favorite_port"}}},
    }  # Assume port connected in port5
    try:
        validate_json(schema, config_snippet)
        o3r.set(config_snippet)
    except json_exceptions.ValidationError:
        pass

    # Before setting an application configuration, erase any previously present app
    o3r.reset("/applications")

    config_snippet = load_config_from_file("configs/ods_one_head_config.json")
    try:
        validate_json(schema, config_snippet)
    except json_exceptions.ValidationError:
        pass
    o3r.set(config_snippet)

    logger.info("You reached the end of the ODSConfig tutorial!")

# %%
