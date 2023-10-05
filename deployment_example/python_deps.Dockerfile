FROM arm64v8/python:3.9.6-slim-buster
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /home/oem/share

# Install dependencies for applications implementing o3r
COPY common_requirements.txt ./requirements.txt
RUN python3 -m pip install -r ./requirements.txt
