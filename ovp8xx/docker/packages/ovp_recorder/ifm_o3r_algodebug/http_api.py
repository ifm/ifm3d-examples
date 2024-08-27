#############################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

# This is a simple HTTP API for the OVP8XX recorder. It allows for starting and stopping recordings, checking the status of the recorder, and listing recordings. Apologies for the excessive use of "global". This is a simple wrapper to get stuff done. It can be improved upon in the future.

import os
import shutil
import random
import time
import logging
from threading import Thread, Event
from pathlib import Path
import socket

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

from ifm3dpy.device import O3R

from recorder import record

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DEFAULT_PORT = int(os.environ.get("OVP_RECORDER_PORT","8000"))
MAX_RECORDING_DURATION = 60
VPU_USB_PATH = "/run/media/system/"
ROTATION_THRESHOLD = float(os.environ.get("ROTATION_THRESHOLD", "-4.0"))
DEFAULT_SAVE_PATH = os.environ.get("SAVE_PATH", "")
ON_OVP: bool = os.environ.get("ON_OVP", "0") in ["1", "true", "True"]
IP = os.environ.get("IFM3D_IP", "192.168.0.69")

recording_lock = Event()
recording_lock.clear()


if not ON_OVP and ROTATION_THRESHOLD < 0:
    logger.warning("Not running on VPU. Ignoring rotation threshold.")

def set_save_path(new_path: str = DEFAULT_SAVE_PATH):
    if ON_OVP and not new_path:
        # check for VPU USB path
        if not os.path.exists(VPU_USB_PATH):
            logger.error(f"VPU USB path {VPU_USB_PATH} not found.")
        else:
            mounts = os.listdir(VPU_USB_PATH)
            if len(mounts) == 0:
                logger.error(f"No VPU USB mounts found in {VPU_USB_PATH}.")
                exit(1)
            else:
                logger.info(f"Found VPU USB mounts: {mounts}")
                # get maount with largest size
                new_path = ""
                size = 0
                for mount in mounts:
                    try:
                        stat = os.statvfs(os.path.join(VPU_USB_PATH, mount))
                        this_size = stat.f_frsize * stat.f_bavail
                        if this_size > size:
                            size = this_size
                            new_path = os.path.join(VPU_USB_PATH, mount, "recordings")
                    except Exception as e:
                        logger.error(
                            f"Error while probing mounted usb {mount}: {e}")
    if new_path and not os.path.exists(new_path):
        os.makedirs(new_path)
    return new_path

save_path = set_save_path()
cache_path = os.path.join(Path(__file__).parent, "recordings")
if not os.path.exists(cache_path):
    os.makedirs(cache_path)
os.chdir(cache_path)

logger.info(f"Using save path: {save_path}")
logger.info(f"Using cache path: {cache_path}")

total_size: int = 0
last_recording: str = ""
last_recording_size: float = 0
available_space: float = float("inf")


def rotate_files(path):
    files = os.listdir(path)
    if len(files) == 0:
        return
    files = [os.path.join(path, f) for f in files if ".h5" in f]
    total_size_all_f = sum(os.path.getsize(f) for f in files)
    files = sorted(files, key=os.path.getctime)
    global last_recording
    last_recording = files[-1]
    global last_recording_size
    last_recording_size = os.path.getsize(last_recording)
    global total_size
    total_size = sum(os.path.getsize(f) for f in files)
    check_space(path)
    global available_space
    if ON_OVP:
        if ROTATION_THRESHOLD < 0:
            while available_space < abs(ROTATION_THRESHOLD) * (1024**3) and len(files) > 0:
                available_space += os.path.getsize(files[0])
                total_size -= os.path.getsize(files[0])
                logger.info(f"pruning {files[0]}")
                os.remove(files.pop(0))
        else:
            while total_size_all_f > ROTATION_THRESHOLD*(1024**3):
                total_size -= os.path.getsize(files[0])
                total_size_all_f -= os.path.getsize(files[0])
                logger.info(f"Removing {files[0]}")
                os.remove(files.pop(0))


def check_space(path):
    if ON_OVP:
        if path:
            stat = os.statvfs(path)
            global available_space
            available_space = stat.f_bavail * stat.f_frsize
            logger.info(
                f"Available space: {available_space/(1024**3)} GiB")
        else:
            available_space = 0
        
def move_recordings():
    # find all .h5 files in cache_path
    files = os.listdir(cache_path)
    files = [f for f in files if ".h5" in f]
    for f in files:
        try:
            # os.rename(os.path.join(cache_path, f), os.path.join(save_path, f))
            shutil.move(os.path.join(cache_path, f), os.path.join(save_path, f))

            logger.info(f"Moved {f} to {save_path}")
        except Exception as e:
            logger.error(f"Error moving {f}: {e}")


class DefaultRecordingParams(BaseModel):
    sources: str = "port2"
    filename: str = ""
    numberOfSeconds: float = 30
    ip: str = "192.168.0.69"
    timeout: float = 3.0
    ProgressBar: bool = True
    autostart: bool = True
    appAutoSource: bool = True
    forceDisableMotionCompensation: bool = False
    useIfm3d: bool = True
    closeConnectionOnTimeout: bool = False
    iVA: bool = True


class ExposedRecordingParams(BaseModel):
    sources: str = "port2"
    filename: str = ""
    numberOfSeconds: float = MAX_RECORDING_DURATION
    autostart: bool = True
    appAutoSource: bool = True
    forceDisableMotionCompensation: bool = False
    useIfm3d: bool = True
    closeConnectionOnTimeout: bool = False
    iVA: bool = True

    def kwargs(self):
        default_dict = DefaultRecordingParams().model_dump()
        default_dict.update(self.model_dump())
        return default_dict


class RecordingThread(Thread):
    def __init__(self, recordingParams: ExposedRecordingParams, recording_lock: Event = recording_lock):
        super().__init__()
        self.recordingParams: ExposedRecordingParams = recordingParams
        self.recording_interrupt = Event()
        self.recording_interrupt.clear()
        self.recording_lock = recording_lock

    def run(self):
        try:
            if self.recording_lock.is_set():
                logger.error("Recording thread already running.")
                return
            else:                
                self.recording_lock.set()
                logger.info(f"Rec. {self.recordingParams.numberOfSeconds} \
                                seconds or until interruption.")
                
                record(interrupt=self.recording_interrupt,
                    **self.recordingParams.kwargs())
                
                logger.info("Recording completed.")
                
                # move the recording to the save path
                if save_path:
                    move_recordings()
                    rotate_files(save_path)
                else:
                    logger.error("No save path found. Rotating files in cache path instead.")
                    rotate_files(cache_path)
                self.recording_lock.clear()
        except Exception as e:
            logger.error(f"Error in recording thread: {e}")
            self.recording_lock.clear()

    def stop(self):
        self.recording_interrupt.set()

# # Usage of RecordingThread class:
# print("Initializing recorder thread...")
# recording_thread = RecordingThread(ExposedRecordingParams())
# recording_thread.start()
# time.sleep(5)
# print("attempting to start a second recording thread...")
# recording_thread2 = RecordingThread(ExposedRecordingParams()) # >>>> Recording thread already running.
# recording_thread2.start()
# time.sleep(5)
# print("Interrupting recording...")
# recording_thread.stop()
# time.sleep(5)
# recording_thread.join()
# print("Recording thread joined.")
# exit()


title = "OVP8XX Recorder API"
description = f"""

---

## Defaults:

**Port**: {DEFAULT_PORT}

**Save path**: "{DEFAULT_SAVE_PATH}" (if empty, will attempt to find the default save path (USB mount directory for the device that was connected to VPU during deployment))

**Rotation threshold**: {ROTATION_THRESHOLD} GiB (negative values will expand to rotation_threshold less than the total available space)

**Max recording duration**: {MAX_RECORDING_DURATION} seconds

---

**Note:**

Recordings will be cached local to the API and moved to the save path after recording is complete.

**Save path found at startup**: "{save_path}"

**Cache path**: "{cache_path}"

If the USB device was not found at start up, recordings will be rotated in the cache path as a fallback.

The docker container will need to be redeployed to mount a new USB device.

If the original usb device was reinserted, the vpu will need to be rebooted to remount the device.

There is no calculation of expected recording size so it will be possible to run out of space during recording. keep recording durations to reasonable sizes (ie. less than the available space as defined by the rotation threshold!).

The recorder will take a second to spin up and a couple seconds to spin down, cleanup, and move the recording to the save path.

---
"""
version = "0.0.0"

tags_metadata = [
    {
        "name": "Set (Reset) Save Path",
        "description": "Set the save path to a particular directory, if empty, will reattempt to find the default save path (VPU USB mount directory). A reboot will be required to remount the USB device if removed and reinserted."
    }
]

recording_tag = "Recording"

app = FastAPI(
    title=title,
    docs_url="/",
    version=version,
    description=description,
    redoc_url=None,
    log_level="INFO",
    openapi_tags=tags_metadata,)

recorder_threads = []

last_recording_params = ExposedRecordingParams()

@app.post("/start", tags=[recording_tag])
def start_recording(params: ExposedRecordingParams):
    global last_recording_params
    last_recording_params = params
    recorder_threads.append(RecordingThread(params))
    try:
        recorder_threads[-1].start()
        return {"status": "Recording started"}
    except Exception as e:
        return {"status": f"Error starting recording: {e}"}
    
@app.post("/start_with_last_settings", tags=[recording_tag])
def start_recording_with_last_settings():
    return start_recording(last_recording_params)

@app.get("/last_settings", tags=[recording_tag])
def get_last_settings():
    return last_recording_params.model_dump()


@app.post("/stop", tags=[recording_tag])
def stop_recording():
    # stop recording
    try:
        for thread in recorder_threads:
            if thread.is_alive():
                thread.stop()
            else:
                recorder_threads.remove(thread)
        return {"status": "Recording interrupted"}
    except Exception as e:
        return {"status": f"Error stopping recording: {e}"}


@app.get("/status", tags=[recording_tag])
def recording_status():
    # get recording status
    try:
        check_space(save_path)
    except Exception as e:
        logger.error(f"Error checking space: {e}")

    return {
        "Status": "Recording" if recording_lock.is_set() else "Idle",
        "Total_GiB recorded.": round(total_size/(1024**3), 3),
        "Last Recording": last_recording,
        "Last Recording GiB": round(last_recording_size/(1024**3), 3),
    }


@app.get("/list", tags=[recording_tag])
def list_recordings():
    # list recordings and their respective ctime and sizes
    try:
        files = os.listdir(save_path)
        files = [f for f in files if ".h5" in f]
        record_times = [os.path.getctime(
            os.path.join(save_path, f)) for f in files]
        files, record_times = zip(*sorted(zip(files, record_times)))
        recordings = []
        # make recording times human readable
        record_times = [time.strftime(
            "%Y-%m-%d %H:%M:%S", time.localtime(ct)) for ct in record_times]
        for f,ct in zip(files, record_times):
            size = os.path.getsize(os.path.join(save_path, f))
            recordings.append({
                "filename": f,
                "size_GiB": round(size/(1024**3), 3),
                "ctime": ct
            })
        return {"recordings": recordings}
    except Exception as e:
        return {"status": f"Error listing recordings: {e}"}

@app.post("/set_save_path", tags=["Set (Reset) Save Path"])
def reset_save_path(new_path: str=""):
    global save_path
    if not new_path:
        new_path = DEFAULT_SAVE_PATH
    save_path = set_save_path(new_path)
    return {"status": f"Save path set to {save_path}"}

@app.post("/reboot", tags=["Set (Reset) Save Path"])
def reboot_vpu():
    o3r = O3R(IP)
    o3r.reboot()



tcp_trigger_port = DEFAULT_PORT+1
class TCP_trigger(Thread):
    def __init__(self, host="0.0.0.0", port=tcp_trigger_port):
        super().__init__()
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((host, port))
        self.server_socket.listen(1)
    
    def run(self):
        while True:
            print("Waiting for TCP connection...")
            client_socket, addr = self.server_socket.accept()
            logger.info(f"Connection from: {addr}")
            data = client_socket.recv(1024).decode()
            logger.info(f"Received: {data}")
            if "stop" in data:
                logger.info(stop_recording())
            elif "reboot" in data:
                logger.info(reboot_vpu())
            else:
                logger.info(start_recording_with_last_settings())
            client_socket.close()


if __name__ == "__main__":

    trigger = TCP_trigger()
    trigger.start()

    logger.info(f"Starting {title}")
    if save_path:
        rotate_files(save_path)
    else:
        rotate_files(cache_path)
    if ON_OVP:
        host = "0.0.0.0"
        # get the host ip address
        o3r = O3R(IP)
        interfaces_state = o3r.get(["/device/network/interfaces"])["device"]["network"]["interfaces"]
        interfaces = "eth0", "eth1"
        external_addresses = [interfaces_state[interface]["ipv4"]["address"] for interface in interfaces]
        logger.info(f"API to be available at: eth0: http://{external_addresses[0]}:{DEFAULT_PORT} or at eth1: http://{external_addresses[1]}:{DEFAULT_PORT}")
        logger.info(f"TCP trigger available at: {host}:{tcp_trigger_port}")
    else:
        host = "127.0.0.1"
    uvicorn.run(app, host=host, port=DEFAULT_PORT, log_level="info")
#%%