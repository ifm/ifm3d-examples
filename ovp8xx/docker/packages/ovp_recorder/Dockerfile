#---
# name: ovp_recorder
# group: ifm3d
# notes: recorder for algo-debug data produced by ovp8xx devices (dusty-nv/jetson-containers package)
# depends: [ifm3d]
#---

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

# --- Install Python dependencies

RUN python3 -m pip install pip
RUN python3 -m pip install pydantic fastapi uvicorn