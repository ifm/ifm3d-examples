# FROM arm64v8/python:3.9.6-slim-buster
# FROM jupyter/tensorflow-notebook:latest
# FROM tverous/pytorch-notebook:latest

# Base linux for tegra (l4t) amr64/aarch64 image
FROM nvcr.io/nvidia/l4t-base:r32.4.3 AS buildstage

# Install necessary updates + git (for cloning the nvidia samples). Tag v10.2 specifies the right commit. VPU runs CUDA 10.2
RUN apt-get update && apt-get install -y --no-install-recommends make g++ git && apt-get install ca-certificates -y
RUN git clone --depth 1 --branch v10.2 https://github.com/NVIDIA/cuda-samples.git /tmp/

# Change into the right directory and install/make the samples
WORKDIR /tmp/Samples/deviceQuery
RUN make clean && make

# Multistage build to reduce the image size on the platform
FROM nvcr.io/nvidia/l4t-tensorrt:r8.0.1-runtime


# Copy the samples from the buildstage into the final image
RUN mkdir -p /usr/local/bin
COPY --from=buildstage /tmp/Samples/deviceQuery/deviceQuery /usr/local/bin

# Execute the deviceQuery and check for CUDA support. Don't forget the runtime with the docker run command
CMD ["/usr/local/bin/deviceQuery"]


#############################################################################
# Install dependencies for applications implementing o3r
COPY tensorrt_example/common_requirements.txt ./requirements.txt
RUN apt-get update && apt-get install -y python3-pip
# RUN python3 -m pip install jax
RUN python3 -m pip install -r ./requirements.txt

ARG DEBIAN_FRONTEND=noninteractive
# WORKDIR /home/oem/

# # TODO simply use pypi in the future
COPY o3r_docker_manager ./o3r_docker_manager
RUN pip install ./o3r_docker_manager
RUN apt-get remove -y make g++ git python3-pip
