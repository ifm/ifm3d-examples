#!/bin/sh

set -e # terminate if a command fails

# Load common variables
. "$(dirname "$0")/config.sh"

# Build the Docker container and forward the SSH Agent to specific commands
build_command=${DOCKER_COMMAND:-"docker build \
                                   --rm \
                                   --pull \
                                   -t ${IFM_DOCKER_IMAGE_NAME}:${VERSION} \
                                   ."}

$build_command --build-arg UBUNTU_VERSION="${OS_VERSION}"
