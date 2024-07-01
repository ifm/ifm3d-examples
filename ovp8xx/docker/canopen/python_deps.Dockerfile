FROM arm64v8/python:3.9.6-slim-buster
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /home/oem/share

# Install dependency for FW1.1.X workaround for CAN baudrate setting
RUN apt-get update
RUN apt-get install iproute2 -y
RUN apt-get install kmod -y
RUN apt-get install can-utils -y

# Install dependencies for applications implementing o3r
COPY canopen/common_requirements.txt ./requirements.txt
# RUN apt-get install python3-pip -y
RUN python3 -m pip install -U pip
RUN python3 -m pip install -r requirements.txt

# run everything as oem
USER ${USER_NAME}
WORKDIR /home/${USER_NAME}/share