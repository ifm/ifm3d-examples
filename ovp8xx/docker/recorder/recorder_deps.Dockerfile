FROM arm64v8/python:3.9.6-slim-buster
ARG DEBIAN_FRONTEND=noninteractive

ARG USER_NAME=oem

# # Add user named oem with uid and gid matching the VPU
# ARG USER_ID=989
# ARG GROUP_ID=988
# RUN groupadd -g ${GROUP_ID} ${USER_NAME} &&\
#     useradd -l -u ${USER_ID} -g ${USER_NAME} ${USER_NAME} &&\
#     install -d -m 0755 -o ${USER_NAME} -g ${USER_NAME} /home/${USER_NAME}

RUN mkdir -p /home/oem/share
# # run everything as oem
# USER ${USER_NAME}
WORKDIR /home/${USER_NAME}/share

# Install dependencies for applications implementing o3r
COPY recorder/common_requirements.txt ./requirements.txt
RUN python3 -m pip install -U pip
RUN python3 -m pip install paramiko
RUN python3 -m pip install -r requirements.txt
