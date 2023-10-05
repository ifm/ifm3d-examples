#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

#%%
import json
import time

import requests
# %%

addr="192.168.0.69"
port: int = 8000

#%%

requests_per_sec = 20
secs_per_zone_setting = 50
last_zone_setting = None
t_elapsed_rolling_average = 0.01
t_worst_request_time = 0.0
t_to_test = 60*60*4
zone_set = 0

for i in range(t_to_test*requests_per_sec):
    
    if False:# i%(requests_per_sec*secs_per_zone_setting):
        zone_set= (zone_set + 1)%7
        if zone_set>6:
            method = "ad_hoc"
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
            }
            data = json.dumps({
                "zone0": [[0,1],[1,1],[1,-1],[0,-1]],
                "zone1": [[1,1],[2,1],[2,-1],[1,-1]],
                "zone2": [[2,1],[3.5,1],[3.5,-1],[2,-1]],
                "index": 65536,
                "maxHeight": 0.5,
                "view": "forward",
            })
        else:
            method = "zone_set"
            headers = {
                "accept": "application/json",
                "Content-Type": "application/json",
            }
            data = json.dumps({"index": 2})
    else:
        method = "sync"
        headers = None
        data = None
        

    msg_start_t = time.perf_counter()
    url = f"http://{addr}:{port}/{method}/"
    if method == "sync":
        response = requests.get(url,headers=headers,data=data)
    else:
        response = requests.post(url, headers=headers, data=data)
    t_elapsed = time.perf_counter() - msg_start_t

    if t_elapsed > t_worst_request_time:
        t_worst_request_time = t_elapsed
    t_elapsed_rolling_average = t_elapsed_rolling_average * 0.99 + t_elapsed * 0.01
    

    if i % (requests_per_sec * 10) == 0:
        print("Rolling ave request latency = ", round(t_elapsed_rolling_average, 5))
        print(
            f"Worst latency (out of {i} requests) = {round(t_worst_request_time,5)}"
        )
    time.sleep(max(0, 1 / requests_per_sec - t_elapsed))
# %%
