#!/bin/bash
set -euo pipefail

# Pull the base image beforehand to take advantage of caching
docker pull arm64v8/python:3.8.16-slim-buster || true

# Build the compile-image stage
docker build --target compile-image -t o3r_data_recorder:compile-stage -f ./Aggregate.Dockerfile .

# Build the final image using the compile-image as cache
docker build --target build-image -t o3r_data_recorder:v0.1.0 .

# Define IP addresses in an array
declare -a ips=("192.168.0.69" "192.168.0.110")

for ip in "${ips[@]}"; do
    if ping -c 1 "$ip" &> /dev/null; then
        # Remove the existing image on the remote server
        sshpass -poem ssh -C oem@"$ip" docker image rm o3r_data_recorder:v0.1.0

        # Transfer and load the new image on the remote server
        docker save o3r_data_recorder:v0.1.0 | sshpass -poem ssh -C oem@"$ip" docker load
    fi
done
