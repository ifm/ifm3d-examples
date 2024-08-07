#---
# name: ifm3d
# group: build
# notes: python dependencies for python demos
# depends: [python, cmake]
#---

ARG BASE_IMAGE
FROM ${BASE_IMAGE}

ARG DEBIAN_FRONTEND=noninteractive

# --- setup share that mirrors the host oem user's home directory

RUN mkdir -p /home/oem/share
WORKDIR /home/oem/share

# --- Install Python dependencies

RUN python3 -m pip install -U pip
COPY requirements.txt ./requirements.txt
RUN python3 -m pip install -r requirements.txt

# --- Install the ifm3d cli/c++ library

ARG IFM3D_VERSION="1.5.3"

# Create the oem user
# RUN id oem 2>/dev/null || useradd --uid 30000 --create-home -s /bin/bash -U oem

WORKDIR /home/oem

RUN set -ex \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    build-essential \
    openssh-server \
    curl \
    nano \
    jq \
    ninja-build \
    coreutils \
    libboost-all-dev \
    libgoogle-glog-dev \
    libgoogle-glog0v5 \
    libproj-dev \
    libssl-dev \
    libxmlrpc-c++8-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    \
    && gcc --version \
    && g++ --version

# Install ifm3d using the deb files
RUN mkdir /home/oem/ifm3d
ADD https://github.com/ifm/ifm3d/releases/download/v${IFM3D_VERSION}/ifm3d-l4t-base-r32.4.3-arm64-debs_${IFM3D_VERSION}.tar /home/oem/ifm3d
RUN cd /home/oem/ifm3d &&\
    tar -xf ifm3d-l4t-base-r32.4.3-arm64-debs_${IFM3D_VERSION}.tar &&  \
    dpkg -i *.deb

RUN git clone --branch v3.11.2 https://github.com/nlohmann/json.git && \
    cd json && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DJSON_BuildTests=OFF .. && \ 
    make && \
    make install && \
    git clone https://github.com/pboettch/json-schema-validator.git && \
    cd json-schema-validator && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DJSON_VALIDATOR_BUILD_TESTS=OFF -DJSON_VALIDATOR_BUILD_EXAMPLES=OFF .. && \
    make && \
    make install 

