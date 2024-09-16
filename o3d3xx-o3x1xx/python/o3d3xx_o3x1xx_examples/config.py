# Configurations for the O3D3xx and 
# O3X1xx examples.
# Edit this file to match your setup.
from pathlib import Path
import os

CURRENT_DIR = Path(__file__).parent.resolve().as_posix()

############################################
# Device configuration
############################################
IP: str = os.environ.get("IFM3D_IP", "192.168.0.22")
