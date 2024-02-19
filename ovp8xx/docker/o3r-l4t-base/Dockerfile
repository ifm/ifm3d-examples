# Copyright (c) 2020-2022, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM docker.io/arm64v8/ubuntu:18.04

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -qq -y --no-install-recommends \
    bc \
    bzip2 \
    language-pack-en-base \
    python3-distutils && \
    rm -rf /var/lib/apt/lists/* && apt-get clean

ARG JETPACK_VERSION_BASE="r32.4"
ARG JETPACK_VERSION="${JETPACK_VERSION_BASE}.3"
ARG BASE_IMAGE="nvcr.io/nvidia/l4t-base:${JETPACK_VERSION}"
ARG SOC="t186"

ADD --chown=root:root https://repo.download.nvidia.com/jetson/jetson-ota-public.asc /etc/apt/trusted.gpg.d/jetson-ota-public.asc
RUN chmod 644 /etc/apt/trusted.gpg.d/jetson-ota-public.asc \
    && apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates \
    && echo "deb https://repo.download.nvidia.com/jetson/common ${JETPACK_VERSION_BASE} main" > /etc/apt/sources.list.d/nvidia-l4t-apt-source.list \
    && echo "deb https://repo.download.nvidia.com/jetson/${SOC} ${JETPACK_VERSION_BASE} main" >> /etc/apt/sources.list.d/nvidia-l4t-apt-source.list \
    && cat /etc/apt/sources.list.d/nvidia-l4t-apt-source.list \
    && apt-get update \
    && rm -rf /var/lib/apt/lists/*
# the last two lines are just to test it works. Leaving the ca-certificates
# package in is intentional, since nvidia uses https sources and without that,
# apt will complain about "Certificate verification failed: The certificate is
# NOT trusted. The certificate issuer is unknown.  Could not handshake: Error
# in the certificate verification. [IP: 23.221.236.160 443]"
# You will probably want to update ca-certificates in each apt stanza in each
# derived image since certificates can be revoked periodically and that package
# should always be up to date.
ARG CUDA=invalid
ENV CUDA=${CUDA}

ENV PATH /usr/local/cuda-$CUDA/bin:/usr/local/cuda/bin:${PATH}
ENV LD_LIBRARY_PATH /usr/local/cuda-$CUDA/targets/aarch64-linux/lib:${LD_LIBRARY_PATH}

RUN ldconfig

ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES all

CMD ["/bin/bash"]
