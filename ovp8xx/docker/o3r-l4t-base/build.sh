#!/bin/sh

set -e # terminate if a command fails

# Load common variables
. "$(dirname "$0")/config.sh"

CUDA="10.2"
JETPACK_VERSION_BASE="r32.4"
JETPACK_VERSION="${JETPACK_VERSION_BASE}.3"

# Build the Docker container and forward the SSH Agent to specific commands
build_command=${DOCKER_COMMAND:-"docker build \
                                   --rm \
                                   --pull \
				   --build-arg CUDA=${CUDA} \
				   --build-arg JETPACK_VERSION_BASE=${JETPACK_VERSION_BASE} \
				   --build-arg JETPACK_VERSION=${JETPACK_VERSION} \
                                   -t ${IFM_DOCKER_IMAGE_NAME}:${VERSION} \
                                   ."}

$build_command --build-arg UBUNTU_VERSION="${OS_VERSION}"
