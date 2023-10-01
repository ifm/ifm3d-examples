FROM arm64v8/python:3.9.6-slim-buster
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /home/oem/share

# Install dependencies for applications implementing o3r
COPY deployment_demo/common_requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt

# TODO simply use pypi in the future
COPY o3r_docker_manager ./o3r_docker_manager
RUN pip install ./o3r_docker_manager
