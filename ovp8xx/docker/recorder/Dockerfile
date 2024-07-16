# SPDX-License-Identifier: Apache-2.0
# Copyright (C) 2024 ifm electronic gmbh
#
# THE PROGRAM IS PROVIDED "AS IS" WITHOUT WARRANTY OF ANY KIND.

FROM arm64v8/python:3.8.16-slim-buster AS compile-image

# Set a non-root user for security reasons
RUN useradd --uid 30000 --create-home -s /bin/bash -U ifm
WORKDIR /home/ifm

# Install necessary packages in a single RUN command for better layer caching
RUN apt-get update && \
    apt-get --no-install-recommends -y install \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-wheel \
    zip \
    build-essential \
    nano && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -U pip && pip install --no-cache-dir -r requirements.txt

RUN find . \( -iname "*.c" -o -iname "*.pyx" \) -delete && \
    rm -f `find /opt/venv -iname "*.js.map"` && \
    rm -rf build/

# Use a separate stage for building the final image
FROM arm64v8/python:3.8.16-slim-buster AS build-image

RUN apt-get update && apt-get -y upgrade && \
    apt-get -y install --no-install-recommends \
    python3-dev \
    nano && \
    apt-get -y clean && \
    rm -rf /var/lib/apt/lists/*

# Set the working directory and copy the application code
WORKDIR /app
COPY . .

# Copy the virtual environment from the compile-image stage
COPY --from=compile-image /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

ENV PYTHONFAULTHANDLER=1
CMD ["bash"]
