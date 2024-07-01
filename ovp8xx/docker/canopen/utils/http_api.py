#############################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################


import logging
import time

# from multiprocessing import Process, Queue
from threading import Thread
from queue import Queue, Empty

import uvicorn
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from pydantic import BaseModel

logger = logging.getLogger(__name__)

DEFAULT_PORT = 8000

class AdHocZoneSetting(BaseModel):
    index: int
    x: int
    y: int
    width: int
    height: int

class ZoneSet(BaseModel):
    index: int


class Frontend:
    """fastapi"""

    def __init__(self, to_frontend, to_backend, log_level, port):
        self.api = FastAPI(docs_url="/", redoc_url=None, log_level=log_level)
        self.to_frontend = to_frontend
        self.to_backend = to_backend
        self.log_level = log_level
        self.port = port

        # Register endpoints
        self.api.post("/ad_hoc/")(self.ad_hoc_zone_setting)
        self.api.get("/sync/")(self.sync)
        self.api.post("/zone_set/")(self.zone_set)

        # Customize /docs
        openapi_schema = get_openapi(
            title="Simple VPU CANopen API",
            version="0.0.0",
            description="write and read CANopen data from the VPU",
            routes=self.api.routes,
        )
        self.api.openapi_schema = openapi_schema

        # initialize state
        self.n_requests = 0
        self.state = {"status": "Backend not yet initialized"}

        self.start = time.perf_counter()

    def run(self):
        uvicorn.run(
            self.api, host="0.0.0.0", port=self.port
        )  # ,log_level=logging.getLevelName(self.log_level))

    async def close(self):
        """Graceful shutdown."""
        logging.warning("Shutting down the app.")

    async def sync(self):
        """Report the state of the parent process."""
        self.n_requests += 1
        logging.info(f"Updating state for http api from: {self.state}")
        self.update_state()
        logging.info(f"Updated state for http api to: {self.state}")
        return self.state

    def update_state(self):
        try:
            self.state = self.to_frontend.get_nowait()
        except Empty:
            pass

    async def ad_hoc_zone_setting(self, item: AdHocZoneSetting):
        """Set dimensions on the fly."""
        self.n_requests += 1
        if self.to_backend.full():
            self.to_backend.get()
        if item:
            self.to_backend.put_nowait(item)
        return "1"

    async def zone_set(self, item: ZoneSet):
        """Set dimensions on the fly."""
        self.n_requests += 1
        logging.info(f"Setting zones_idx to {item.index}")
        if self.to_backend.full():
            self.to_backend.get()
        if item:
            self.to_backend.put_nowait(item)
        logging.info(f"Set zones_idx to {item.index}")
        return "1"


class Backend:
    def set_vpu_status(self, status):
        self.backend_state["odsMode"] = status

    def set_zones_occ(self, occupancy):
        self.backend_state["occupancy"] = occupancy

    def set_zones(self, zone_set):
        self.backend_state["zones"] = zone_set

    def push(self):
        if self.to_frontend.full():
            self.to_frontend.get()
        self.to_frontend.put_nowait(self.backend_state)

    def recv(self):
        self.update_state()
        return self.front_end_state

    def __init__(self, log_level="WARNING", port=DEFAULT_PORT, **kwargs):
        self.to_backend = Queue(maxsize=1)
        self.to_frontend = Queue(maxsize=1)
        p = Thread(
            target=self.api_runner,
            args=(self.to_frontend, self.to_backend, log_level, port),
        )
        p.start()
        self.n_requests = 0
        self.requests_since_last_check = 0
        self.app = None
        self.front_end_state: BaseModel = ZoneSet(index=0)
        self.backend_state = {"msg_cnt": 0, "status": "winning"}
        self.push()

    def api_runner(self, to_frontend, to_backend, log_level, port):
        app = Frontend(to_frontend, to_backend, log_level, port)
        app.run()

    def update_state(self):
        try:
            self.front_end_state = self.to_backend.get_nowait()
        except Empty:
            pass

    def sync(self, msg) -> dict:
        self.update_state()
        if self.to_frontend.full():
            self.to_frontend.get()
        self.to_frontend.put(msg, block=False)
        return self.front_end_state
