FFROM arm64v8/alpine

RUN apk add --no-cache python3 py3-pip

# Create a venv and install python dependencies
RUN python3 -m venv /home/ifm/venv \
    && /home/ifm/venv/bin/pip install --upgrade pip \
    && /home/ifm/venv/bin/pip install canopen

# upload the python and eds files, make sure they are in same folder as this Dockerfile
COPY can_example.py /usr/local/bin
COPY DTM425.eds /usr/local/share

# Make the script executable
RUN chmod +x /usr/local/bin/can_example.py

# Activate virtual environment and run the script
CMD ["/home/ifm/venv/bin/python", "/usr/local/bin/can_example.py"]