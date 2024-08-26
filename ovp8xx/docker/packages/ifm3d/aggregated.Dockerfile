
ARG BASE_IMAGE="nvcr.io/nvidia/l4t-base:r32.7.1"
FROM ${BASE_IMAGE}


# --- install build-essentials and the latest stable version of cmake

ENV DEBIAN_FRONTEND=noninteractive \
    LANGUAGE=en_US:en \
    LANG=en_US.UTF-8 \
    LC_ALL=en_US.UTF-8
    #TERM=dumb

RUN set -ex \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        locales \
        locales-all \
        tzdata \
    && locale-gen en_US $LANG \
    && update-locale LC_ALL=$LC_ALL LANG=$LANG \
    && locale \
    \
    && apt-get install -y --no-install-recommends \
        build-essential \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        lsb-release \
        pkg-config \
        gnupg \
        git \
        gdb \
        wget \
        curl \
        nano \
        zip \
        unzip \
        time \
	    sshpass \
	    ssh-client \
    && apt-get clean \
    && apt-get autoremove \ 
    && gcc --version \
    && g++ --version 

# --- install python>=3.8 for compatibility with ifm3dpy

ARG PYTHON_VERSION_ARG=3.8

ENV PYTHON_VERSION=${PYTHON_VERSION_ARG} \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100 \
    PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONIOENCODING=utf-8 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=off \
    PIP_CACHE_PURGE=true \
    PIP_ROOT_USER_ACTION=ignore \
    TWINE_NON_INTERACTIVE=1 \
    DEBIAN_FRONTEND=noninteractive

COPY install_python_l4t.sh /tmp/install_python.sh 
RUN /bin/bash /tmp/install_python.sh

ARG DEBIAN_FRONTEND=noninteractive

# --- upgrade cmake via pip

RUN set -ex \
    && pip3 install --upgrade --force-reinstall --no-cache-dir --verbose cmake \
    \
    && cmake --version \
    && which cmake


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

