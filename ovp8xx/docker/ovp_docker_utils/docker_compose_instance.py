
from typing import List, Tuple

import yaml
from pydantic import BaseModel, model_validator


class DockerComposeServiceInstance(BaseModel):
    """
    A class to hold the information needed to deploy a docker-compose service instance to the OVP

    For simplicity, use one docker-compose file for each service instance.

    Multiple containers can be deployed from a single docker-compose file using different service names but the autostart daemon will only launch the file using `docker-compose -f <file> up -d` once.
    """
    docker_compose_src_on_pc: str
    docker_compose_dst_on_vpu: str
    additional_project_files_to_transfer: List[Tuple[str, str]] = []

    # The following are optional and can be used to specify the docker image to load onto the OVP
    # prefer to pull from registry if possible
    tag_to_pull_from_registry: str = None
    # otherwise, load from a tar file on the host machine
    docker_image_src_on_pc: str = None
    docker_image_dst_on_vpu: str = None

    docker_compose: dict = {}

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
