
from typing import List, Tuple, Union

import yaml
from pydantic import BaseModel, model_validator


class RemoteTarSpec(BaseModel):
    url: str = ""
    checksum: str = ""

class FileSystemMapping(BaseModel):
    src: str
    dst_volume: str
    dst_build: str = None # optional specification of where in the container to move the file
    exclude_regex: Union[str, None] = None



class DockerComposeServiceInstance(BaseModel):
    """
    A class to hold the information needed to deploy a docker-compose service instance to the OVP

    For simplicity, use one docker-compose file for each service instance.

    Multiple containers can be deployed from a single docker-compose file using different service names but the autostart daemon will only launch the file using `docker-compose -f <file> up -d` once.
    """
    # new
    remote_tar: RemoteTarSpec = RemoteTarSpec()
    file_system_mappings: List[FileSystemMapping] = []
    tmp_dir_on_vpu: str = "/home/oem/tmp"
    
    # keep
    tag_to_run: str = None
    docker_compose: dict = {}

    # deprecate
    project_file_mapping: List[Tuple[str, str]] = []
    docker_compose_src_on_pc: str
    docker_compose_dst_on_vpu: str
    docker_image_src_on_pc: str = None
    docker_image_dst_on_vpu: str = None


    @model_validator(mode='after')
    def _validate(self) -> 'DockerComposeServiceInstance':
        if not (self.docker_compose_src_on_pc.endswith(".yml") or self.docker_compose_src_on_pc.endswith(".yaml")):
            raise ValueError(
                "docker_compose_src_on_pc must be a path to a yaml file")
        if not self.docker_compose:
            with open(self.docker_compose_src_on_pc, "r") as f:
                self.docker_compose = yaml.load(f, yaml.BaseLoader)
        return self

    def write_docker_compose(self, path: str = None):
        if not path:
            path = self.docker_compose_src_on_pc
        with open(path, "w") as f:
            yaml.dump(self.docker_compose, f)

    @property
    def service_name(self):
        return list(self.docker_compose["services"].keys())[0]

    @property
    def docker_repository_name(self):
        return self.docker_compose["services"][self.service_name]["image"]

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
