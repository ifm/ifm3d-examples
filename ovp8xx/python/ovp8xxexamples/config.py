# Configurations for the OVP8xx examples.
# Edit this file to match your setup.
import pathlib
CURRENT_DIR = pathlib.Path(__file__).parent.resolve().as_posix()

############################################
# Device configuration
############################################
IP: str = "192.168.0.69"
PORT_2D: str = "port0"
PORT_3D: str = "port2"
PORT_IMU: str= "port6"

############################################
# ODS configuration
############################################
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

############################################
# Sample data
############################################
SAMPLE_DATA: str = CURRENT_DIR + "/toolbox/test_rec_222.h5"