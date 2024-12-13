#############################################
# Copyright 2023-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
# %%############################################
# In the following, we will demonstrate how to configure an ODS application
# with presets and how to load a specific preset.
# This example assumes two 3D cameras connected on Port2 and Port3.

import logging
import pathlib
import time
import json
from ifm3dpy.device import O3R, Error

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Device specific configuration
IP = "192.168.0.69"
o3r = O3R(IP)

# Load path of the config files
config_path = pathlib.Path(__file__).parent.resolve()

# Reset all application to ensure a clean state before running the example
try:
    o3r.reset("/applications/instances")
except Error as e:
    logger.warning(f"Reset failed: {e}")

# Load and set extrinsic config
with open(config_path / "configs/extrinsic_two_heads.json", "r") as file:
    extrinsic_config = json.load(file)
o3r.set(extrinsic_config)
logger.info("Set the extrinsic calibration")

# Load and set ods config with presets
with open(config_path / "configs/ods_two_heads_presets.json", "r") as file:
    preset_config = json.load(file)
o3r.set(preset_config)
logger.info("Set the ODS application with presets")

# Set ODS application to RUN
ods_config = o3r.get(["/applications/instances/app0/state"])
logger.debug("Set ODS application to RUN")
ods_config["applications"]["instances"]["app0"]["state"] = "RUN"
o3r.set(ods_config)

# Load a predefined preset using its identifier
preset_idx = 2
o3r.set(
    {
        "applications": {
            "instances": {
                "app0": {
                    "presets": {"load": {"identifier": preset_idx}, "command": "load"}
                }
            }
        }
    }
)
loaded_preset = o3r.get(["/applications/instances/app0/presets/load"])
logger.info(f"Loaded preset: {loaded_preset}")

time.sleep(5)
# Loading another preset
logger.info("Loading another preset")
preset_idx = 1
o3r.set(
    {
        "applications": {
            "instances": {
                "app0": {
                    "presets": {"load": {"identifier": preset_idx}, "command": "load"}
                }
            }
        }
    }
)
loaded_preset = o3r.get(["/applications/instances/app0/presets/load"])
logger.info(f"Loaded preset: {loaded_preset}")
