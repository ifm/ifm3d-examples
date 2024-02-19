# shellcheck shell=sh
set -e # terminate if a command fails

# we do use some BuildKit feature like ssh mounts
DOCKER_BUILDKIT=1
export DOCKER_BUILDKIT

VERSION="0.0.1"
export VERSION

IFM_DOCKER_IMAGE_NAME="o3r-l4t-tensorrt"
export IFM_DOCKER_IMAGE_NAME
