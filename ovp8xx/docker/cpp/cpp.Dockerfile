ARG ARCH="amd64"
ARG BASE_IMAGE="ifm3d"
ARG BUILD_IMAGE_TAG="humble"
ARG FINAL_IMAGE_TAG="humble-ros-core"
ARG IFM3D_ROS2_BRANCH="master"
ARG IFM3D_ROS2_REPO="https://github.com/ifm/ifm3d-ros2.git"
ARG IFM3D_VERSION="1.5.3"
ARG UBUNTU_VERSION="22.04"

FROM ubuntu:${UBUNTU_VERSION} as BASE_IMAGE
ARG ARCH
ARG IFM3D_ROS2_BRANCH
ARG IFM3D_ROS2_REPO
ARG IFM3D_VERSION
ARG UBUNTU_VERSION

# Create the ifm user
RUN id ifm 2>/dev/null || useradd --uid 30000 --create-home -s /bin/bash -U ifm
WORKDIR /home/ifm

# Dependencies for both ifm3d and ifm3d-ros2
ARG DEBIAN_FRONTEND=noninteractive
RUN DEBIAN_FRONTEND=noninteractive apt-get update
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    cmake \
    coreutils \ 
    git \
    wget \
    jq \
    libboost-all-dev \
    libgoogle-glog-dev \
    libgoogle-glog0v5 \
    libproj-dev \
    libssl-dev \
    libxmlrpc-c++8-dev

# Install ifm3d using the deb files
RUN mkdir /home/ifm/ifm3d
ADD https://github.com/ifm/ifm3d/releases/download/v${IFM3D_VERSION}/ifm3d-ubuntu-${UBUNTU_VERSION}-${ARCH}-debs_${IFM3D_VERSION}.tar /home/ifm/ifm3d
RUN cd /home/ifm/ifm3d &&\
    tar -xf ifm3d-ubuntu-${UBUNTU_VERSION}-${ARCH}-debs_${IFM3D_VERSION}.tar &&  \
    dpkg -i *.deb

RUN apt-get update
RUN apt-get -y upgrade
RUN apt-get install -y build-essential
RUN DEBIAN_FRONTEND=noninteractive apt-get install -y cmake
RUN apt-get install -y coreutils
RUN apt-get install -y git
RUN apt-get install -y jq
RUN apt-get install -y ninja-build

# c++ examples
WORKDIR /home/oem
# Need to install a more recent version of nlhomann json
# than what is provided by apt, to use with the schema validator.
RUN git clone --branch v3.11.2 https://github.com/nlohmann/json.git && \
    cd json && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DJSON_BuildTests=OFF .. && \ 
    make && \
    make install 
    
RUN git clone https://github.com/pboettch/json-schema-validator.git && \
    cd json-schema-validator && \
    mkdir build && \
    cd build && \
    cmake -DCMAKE_INSTALL_PREFIX=/usr -DJSON_VALIDATOR_BUILD_TESTS=OFF -DJSON_VALIDATOR_BUILD_EXAMPLES=OFF .. && \
    make && \
    make install 


RUN mkdir /home/oem/share

# Copy the cpp examples
ADD --chown=oem cpp /home/oem/cpp
RUN rm -rf /home/oem/cpp/build
WORKDIR /home/oem/cpp/build
ARG IFM3D_VERSION
RUN cmake -DIFM3D_VERSION=${IFM3D_VERSION} .. && cmake --build .
