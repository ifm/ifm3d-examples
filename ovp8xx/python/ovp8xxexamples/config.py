# Configurations for the OVP8xx examples.
# Edit this file to match your setup.
import pathlib

############################################
# Device configuration
############################################
IP: str = "192.168.0.69"
PORT_2D: str = "port0"
PORT_3D: str = "port2"

############################################
# ODS configuration
############################################
CURRENT_DIR = pathlib.Path(__file__).parent.resolve().as_posix()
CALIB_CFG_FILE: str = CURRENT_DIR + "/ods/configs/extrinsic_one_head.json"
ODS_CFG_FILE: str = CURRENT_DIR + "/ods/configs/ods_one_head_config.json"

############################################
# Logging configuration
############################################
LOG_TO_FILE: bool = False

############################################
# NTP configuration
############################################
LOCAL_IP: str = "192.168.0.111"
