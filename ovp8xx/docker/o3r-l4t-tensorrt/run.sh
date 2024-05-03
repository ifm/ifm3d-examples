#!/bin/bash

# Load common variables
source config.sh

docker run \
    -it \
    "${IFM_DOCKER_IMAGE_NAME}:${VERSION}"
