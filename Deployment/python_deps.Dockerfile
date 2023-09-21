FROM arm64v8/python:3.9.6-slim-buster
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /home/oem

# Install some common dependencies for applications implementing o3r
COPY python_deps.txt ./requirements.txt
RUN pip install -U pip && pip install -r ./requirements.txt && rm ./requirements.txt
