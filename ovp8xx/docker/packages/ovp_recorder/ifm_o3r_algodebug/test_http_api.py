#%%##########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################


#%%
from http_api import app, logger, ExposedRecordingParams

import requests
import os
import time
from pprint import pprint as pp

ip = os.environ.get("IFM3D_IP","192.168.0.69")
port = 8000

base_url = f"http://{ip}:{port}"

def get_status():
    response = requests.get(base_url+"/status")
    return response.json()
def get_list():
    response = requests.get(base_url+"/list")
    return response.json()
def start_recording(
        t: float = 10.0,
        sources: list = [
            "port2",
        ]
    ):
    response = requests.post(base_url+"/start", json={
        "numberOfSeconds": t,
        "sources": ",".join(sources)
    })
    return response.json()
def stop_recording():
    response = requests.post(base_url+"/stop")
    return response.json()
# %%
from random import random

for x in range(10000):
    try:
        print("==="*10)
        print(f"Test {x}")
        pp(get_status())
        time.sleep(1)
        # pp(get_list())
        time.sleep(1)
        rest_time = random()*5 +5
        pp( start_recording(
            t= rest_time,
            sources = [
                "port2",
            ],
            ))
        rest_time += 20
        print(f"Sleeping for {rest_time} seconds")
        time.sleep(rest_time)
        # pp(stop_recording())
        # time.sleep(t)
        pp(get_status())
    except Exception as e:
        print(e)
        time.sleep(5)
# %%
