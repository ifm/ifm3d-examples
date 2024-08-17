# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

from typing import List, Tuple, Union

from pydantic import BaseModel, model_validator


class RemoteTarSpec(BaseModel):
    url: str = ""
    fname:str = ""
    sha_256: str = ""

class FileSystemMapping(BaseModel):
    src: str
    dst: str
    exclude_regex: Union[str, None] = None

class DockerComposeServiceInstance(BaseModel):
    """
    A class to hold the information needed to deploy a docker-compose service instance to the OVP

    For simplicity, use one docker-compose file for each service instance.

    Multiple containers can be deployed from a single docker-compose file using different service names but the autostart daemon will only launch the file using `docker-compose -f <file> up -d` once.
    """
    
    remote_tar: Union[None,RemoteTarSpec] = None
    file_system_mappings: List[FileSystemMapping] = []
    tmp_dir_on_vpu: str = "/home/oem/tmp"
    tag_to_run: str = None
    cloud_host_tag: str = None # reference to dockerhub, ghcr.io, nvcr.io or similar may be the same as tag_to_run
    docker_compose: dict = {}

    @property
    def service_name(self):
        return list(self.docker_compose["services"].keys())[0]

    # TODO add a validator to ensure that the tag_to_run is in the docker-compose file
    # @property
    # def tag_to_run(self):
    #     return self.docker_compose["services"][self.service_name]["image"]


    @property
    def container_name(self):
        return self.docker_compose["services"][self.service_name]["container_name"]

    @property
    def log_driver(self):
        if "logging" not in self.docker_compose["services"][self.service_name]:
            return None
        if "driver" not in self.docker_compose["services"][self.service_name]["logging"]:
            return None
        return self.docker_compose["services"][self.service_name]["logging"]["driver"]
