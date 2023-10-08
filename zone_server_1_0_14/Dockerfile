FROM arm64v8/python:3.9.6-slim-buster
ARG DEBIAN_FRONTEND=noninteractive
WORKDIR /home/oem
RUN pip install -U pip

# per volume mount requirements
RUN mkdir share

# General requirements for zone server
COPY requirements.txt ./requirements.txt
# concatenate requirements for specific desired adapters
COPY aggregate_adapter_dependencies.py ./aggregate_adapter_dependencies.py
RUN mkdir src
ADD src/adapters src/adapters
ADD configs ./configs
RUN python3 aggregate_adapter_dependencies.py

RUN pip install -r ./requirements.txt
