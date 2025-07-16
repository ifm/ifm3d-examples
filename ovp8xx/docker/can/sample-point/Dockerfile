FROM arm64v8/alpine
# Install required packages
RUN apk add --no-cache iproute2 can-utils
# Create a script to change sample-point and bitrate
RUN echo -e "#!/bin/ash \
    ip link set can0 down \
    ip link set can0 type can bitrate 250000 sample-point 0.5 \
    ip link set can0 up" > /usr/local/bin/setup_can0.sh
# Make the script executable
RUN chmod +x /usr/local/bin/setup_can0.sh
# Run the script when the container starts
CMD ["/usr/local/bin/setup_can0.sh"]
