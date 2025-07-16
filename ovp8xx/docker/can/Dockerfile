FROM arm64v8/alpine

RUN apk add --no-cache python3 py3-pip

COPY requirements.txt /home/ifm/
# Create a venv and install python dependencies
RUN python3 -m venv /home/ifm/venv \
    && /home/ifm/venv/bin/pip install --requirement /home/ifm/requirements.txt

# Copy the can_example.py example.
COPY can_example.py /home/ifm/
# Copy the eds file to the container
# You can download the DTM425.eds file from https://www.ifm.com/us/en/product/DTM425?tab=documents
COPY DTM425.eds /usr/local/share

# Make the script executable
RUN chmod +x /home/ifm/can_example.py

# Activate virtual environment and run the script
CMD ["/home/ifm/venv/bin/python", "/home/ifm/can_example.py"]
