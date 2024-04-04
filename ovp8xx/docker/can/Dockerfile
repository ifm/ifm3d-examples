FROM arm64v8/alpine

RUN apk add --no-cache python3 py3-pip

# Create a venv and install python dependencies
RUN python3 -m venv /home/ifm/venv \
    && /home/ifm/venv/bin/pip install canopen

# Copy the can_example.py example from ovp8xx/python/ovp8xxexamples/core/ to the folder containing the Dockerfile.
COPY can_example.py /usr/local/bin
# Download the DTM425.eds file from https://www.ifm.com/us/en/product/DTM425?tab=documents
COPY DTM425.eds /usr/local/share

# Make the script executable
RUN chmod +x /usr/local/bin/can_example.py

# Activate virtual environment and run the script
CMD ["/home/ifm/venv/bin/python", "/usr/local/bin/can_example.py"]