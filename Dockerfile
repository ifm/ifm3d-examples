ARG IFM3D_VERSION=v1.4.3
ARG PLATFORM=ubuntu-arm64
ARG CMAKE_VERSION=3.20.6

FROM ghcr.io/ifm/ifm3d:${IFM3D_VERSION}-${PLATFORM}
ARG CMAKE_VERSION

WORKDIR /home/ifm
RUN sudo apt-get update \
    && DEBIAN_FRONTEND=noninteractive sudo apt-get install -y \
        git \
        ninja-build \
        wget 

# Install cmake
RUN wget -O - "https://github.com/Kitware/CMake/releases/download/v${CMAKE_VERSION}/cmake-${CMAKE_VERSION}-linux-$(uname -i).tar.gz" \
    | sudo tar -xz --strip-components=1 -C /usr

# Install JSON and JSON validator
WORKDIR /home/ifm/third-party
RUN git clone --branch v3.11.2 https://github.com/nlohmann/json.git &&\
    cd json &&\
    mkdir build &&\
    cd build &&\
    cmake -GNinja -DJSON_BuildTests=OFF .. &&\
    cmake --build . &&\
    sudo cmake --build . --target install
RUN git clone --branch main https://github.com/pboettch/json-schema-validator.git &&\
    cd json-schema-validator &&\
    mkdir build &&\
    cd build &&\
    cmake -GNinja .. &&\
    cmake --build . &&\
    sudo cmake --build . --target install

# Copy and build c++ examples
WORKDIR /home/ifm
ADD ./Cpp Cpp
WORKDIR /home/ifm/Cpp/build
RUN cmake .. && cmake --build .

# Copy python examples and install requirements
WORKDIR /home/ifm
ADD ./Python Python
RUN . ./venv/bin/activate && pip install -r /home/ifm/Python/requirements.txt