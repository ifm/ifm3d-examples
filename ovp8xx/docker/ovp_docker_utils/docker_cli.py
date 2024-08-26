# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import logging
import os
from pathlib import Path
import colorama
from typing import List

from ovp_docker_utils.cli import cli_tee, convert_nt_to_wsl

logger = logging.getLogger()

def build(
    build_dir=".",
    dockerfile_path: str = "",
    tag: str = "example_build",
    build_args: dict = {},
    os_target: str = "linux",
    arch: str = "arm64",
    target: str = "",
    Additional_build_params: str = "",
):
    
    logger.info(f"Attempting docker build")

    build_dir = Path(build_dir).resolve().as_posix()
    if os.name == "nt" and os_target != "windows":
        build_dir = convert_nt_to_wsl(build_dir)
        dockerfile_path = convert_nt_to_wsl(Path(dockerfile_path).resolve().as_posix())
       
    build_arg_str = " ".join(
            [f"--build-arg=\"{key}={value}\"" for key, value in build_args.items()])
    
    target_str = ""
    if target:
        target_str = f"--target {target}"

    dockerfile_arg = ""
    if dockerfile_path:
        dockerfile_arg = f" -f {dockerfile_path}"

    outputs = {}
    build_cmd = f"docker buildx build {build_arg_str} {target_str} --rm --platform {os_target}/{arch} {dockerfile_arg} {Additional_build_params} {build_dir} -t {tag}"

    outputs[build_cmd] = cli_tee(build_cmd,wsl=True, pty=True)

    return outputs


def save_docker_image(
    tag: str = "example_build",
    docker_build_output_path: str = "",
):
    if docker_build_output_path:
        if os.name == "nt": 
            docker_build_output_path = convert_nt_to_wsl(
                docker_build_output_path)
        docker_save_cmd = f'docker save  {tag} > {docker_build_output_path}'
        
        return {docker_save_cmd: cli_tee(docker_save_cmd,wsl=True, pty=True)}  
    
def load_docker_image(
    tar_path: str = "",
    tag: str = "example_tag",
):
    if os.name == "nt": 
        tar_path = convert_nt_to_wsl(
            tar_path)
    docker_load_cmd = f'docker load < {tar_path}'
    
    return {docker_load_cmd: cli_tee(docker_load_cmd,wsl=True, pty=True)}

def pull_docker_image(
    tag,
):
    cmd = f"docker pull {tag}"
    
    return {cmd: cli_tee(cmd,wsl=True, pty=True)}


def parse_docker_table_output(docker_table: List[str]) -> List[dict]:
    """
    This function structures the output of a docker table into a list of dictionaries    
    """
    params = [param.strip() for param in docker_table[0].split("  ")if param]
    param_starting_positions = []
    param_end_positions = []
    cursor = 0
    for param in params:
        for i in range(cursor, len(docker_table[0])):
            if docker_table[0][i:].startswith(param):
                param_starting_positions.append(i)
                cursor = i + len(param)
                break
    param_end_positions = param_starting_positions[1:] + [
        max([len(line) for line in docker_table])]
    entry_dicts = []
    for running_container in docker_table[1:]:
        container_dict = {}
        for param, param_starting_position, param_end_position in zip(params, param_starting_positions, param_end_positions):
            container_dict[param] = running_container[param_starting_position:param_end_position].strip(
            )
        entry_dicts.append(container_dict)
    return entry_dicts

def tag_docker_image(
    tag: str = "example_tag",
    new_tag: str = "example_tag",
):
    tag_cmd = f'docker tag {tag} {new_tag}'
    
    return {tag_cmd: cli_tee(tag_cmd,wsl=True, pty=True)}

def push_docker_image(
    tag: str = "example_tag",
    registry_host: str = None,
    registry_port=5000,
    throw_error_on_fail: bool = True,
):
    outputs = {}
    if registry_host:
        registry_tag = f"{registry_host}:{registry_port}/{tag}"
        
        outputs = tag_docker_image(tag, registry_tag)

        reg_push_cmd = f'docker push {registry_tag}'
        outputs[reg_push_cmd] = cli_tee(reg_push_cmd,wsl=True, pty=True)
        if throw_error_on_fail:
            # check return code
            if outputs[reg_push_cmd][0] != 0 :
                raise Exception(f"Error pushing image")
            elif "connection refused" in outputs[reg_push_cmd][1][-1].decode().lower():
                raise Exception(f"Error pushing image: connection refused (is the registry running?)")
    return outputs

def prep_image_for_transfer(
    docker_build_output_path: str = "",
    tag: str = "example_build",
    registry_host: str = None,
    registry_port=5000,
    start_tag: str = None,
):
    outputs = {}
    if not start_tag:
        start_tag = tag
    if registry_host and tag:
        outputs = push_docker_image(
            tag=start_tag,
            registry_host=registry_host,
            registry_port=registry_port,
        )
    if docker_build_output_path:
        outputs = save_docker_image(
            tag=start_tag,
            docker_build_output_path=docker_build_output_path,
        )
    
    return outputs



docker_dir_abs = Path(__file__).parent.parent
docker_dir = docker_dir_abs
if os.name == "nt":
    docker_dir = Path(convert_nt_to_wsl(docker_dir_abs.as_posix()))

dustynv_origin = "https://github.com/stedag/jetson-containers.git"
commit = "0414a34b"
jetson_containers_dir = docker_dir / "ovp_docker_utils" /"jetson-containers"

def get_dusty_nv_repo_if_not_found():
    jetson_containers_dir = docker_dir_abs/ "ovp_docker_utils" / "jetson-containers"
    if not (jetson_containers_dir).exists():
        logger.warn(f"jetson-containers repo not found at {jetson_containers_dir}")
        # clone the repo
        # confirm that the user wants the repo cloned
        input("Press enter to clone the jetson-containers repo (CTRL+C to cancel)")
        cmd = f"git clone {dustynv_origin} {jetson_containers_dir}"
        print(colorama.Fore.GREEN + f"Running command: {cmd}" + colorama.Style.RESET_ALL)
        r, o, e = cli_tee(cmd)
        if r != 0:
            raise Exception(f"Error cloning repo: {o}")
        cmd = f"cd {jetson_containers_dir} && git checkout {commit}"
        print(colorama.Fore.GREEN + f"Running command: {cmd}" + colorama.Style.RESET_ALL)
        r, o, e = cli_tee(cmd)
    return jetson_containers_dir.exists()

# TODO - verify that the jetson-containers repo is available

jetson_exec = (jetson_containers_dir /"jetson-containers").as_posix()


def dustynv_build(
    packages: list,
    repo_name: str,
    L4T_VERSION: str,
    CUDA_VERSION: str,
    PYTHON_VERSION: str,
    LSB_RELEASE: str,

    jetson_exec: str = jetson_exec,
    BUILDKIT: bool = True,
    pty: bool = True,
    additional_package_dirs: list = [],
):
    if additional_package_dirs and isinstance(additional_package_dirs, str):
        additional_package_dirs = [additional_package_dirs]

    additional_package_dirs = [Path(convert_nt_to_wsl(p)).as_posix() for p in additional_package_dirs]

    cmd = f"""env L4T_VERSION={L4T_VERSION} \
CUDA_VERSION={CUDA_VERSION} \
PYTHON_VERSION={PYTHON_VERSION} \
LSB_RELEASE={LSB_RELEASE} \
BUILDKIT={int(BUILDKIT)} \
BUILD_WITH_PTY={int(pty)} \
{jetson_exec} build \
--package-dirs '{','.join(additional_package_dirs)}' --skip-tests all \
--name {repo_name} {' '.join(packages)}"""
    
    tag = f"{repo_name}:r{L4T_VERSION}-cu{CUDA_VERSION.replace('.','')}-cp{PYTHON_VERSION.replace('.','')}"

    print(colorama.Fore.GREEN + f"Running command: {cmd}" + colorama.Style.RESET_ALL)
    r, o, e = cli_tee(cmd, wsl=True, pty=True)

    return r, o, tag


