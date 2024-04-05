FROM arm64v8/alpine

RUN apk add --no-cache python3 py3-pip

# Create a venv and install python dependencies
RUN python3 -m venv /home/ifm/venv \
    && /home/ifm/venv/bin/pip install canopen==2.2.0

COPY can_example.py /home/ifm
COPY DTM425.eds /usr/local/share

# Make the script executable
RUN chmod +x /home/ifm/can_example.py

# Activate virtual environment and run the script
CMD ["/home/ifm/venv/bin/python", "/home/ifm/can_example.py"]