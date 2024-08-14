# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
import sys
import logging
import os
from pathlib import Path
import colorama

from ovp_docker_utils.cli import cli_tee, convert_nt_to_wsl

logger = logging.getLogger()

logging.basicConfig()


def docker_build(
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
    build_cmd = f"docker buildx build {build_arg_str} {target_str} --platform {os_target}/{arch} {dockerfile_arg} {Additional_build_params} {build_dir} -t {tag}"

    print(colorama.Fore.GREEN + f"Running command: {build_cmd}" + colorama.Style.RESET_ALL)
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
        print(colorama.Fore.GREEN + f"Running command: {docker_save_cmd}" + colorama.Style.RESET_ALL)
        return {docker_save_cmd: cli_tee(docker_save_cmd,wsl=True, pty=True)}  

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
        registry_tag = f"{registry_host}:{registry_port}/{tag}"
        tag_for_reg_cmd = f'docker tag {start_tag} {registry_tag}'
        reg_push_cmd = f'docker push {registry_tag}'


        print(colorama.Fore.GREEN + f"Running command: {tag_for_reg_cmd}" + colorama.Style.RESET_ALL)
        outputs[tag_for_reg_cmd] = cli_tee(tag_for_reg_cmd,wsl=True, pty=True)    
        print(colorama.Fore.GREEN + f"Running command: {reg_push_cmd}" + colorama.Style.RESET_ALL)
        outputs[reg_push_cmd] = cli_tee(reg_push_cmd,wsl=True, pty=True)
    if docker_build_output_path:
        outputs = save_docker_image(
            tag=start_tag,
            docker_build_output_path=docker_build_output_path,
        )
    
    return outputs



ovp_docker_utils_dir_abs = Path(__file__).parent
ovp_docker_utils_dir = ovp_docker_utils_dir_abs
if os.name == "nt":
    ovp_docker_utils_dir = Path(convert_nt_to_wsl(ovp_docker_utils_dir_abs.as_posix()))

dustynv_origin = "https://github.com/stedag/jetson-containers.git"
commit = "0414a34b"
jetson_containers_dir = ovp_docker_utils_dir / "jetson-containers"

def get_dusty_nv_repo_if_not_found():
    jetson_containers_dir = ovp_docker_utils_dir_abs / "jetson-containers"
    if not (jetson_containers_dir).exists():
        f"jetson-containers repo not found at {jetson_containers_dir}"
        # clone the repo
        # confirm that the user wants the repo cloned
        input("Press enter to clone the jetson-containers repo (CTRL+C to cancel)")
        cmd = f"git clone {dustynv_origin} {jetson_containers_dir}"
        print(colorama.Fore.GREEN + f"Running command: {cmd}" + colorama.Style.RESET_ALL)
        ret, output = cli_tee(cmd)
        if ret != 0:
            raise Exception(f"Error cloning repo: {output}")
        cmd = f"cd {jetson_containers_dir} && git checkout {commit}"
        print(colorama.Fore.GREEN + f"Running command: {cmd}" + colorama.Style.RESET_ALL)
        ret, output = cli_tee(cmd)

# TODO - verify that the jetson-containers repo is available

jetson_exec = (jetson_containers_dir /"jetson-containers").as_posix()
ifm3d_package_dirs = ",".join(
    (
        (ovp_docker_utils_dir/"ovp8xx"/"docker"/"packages/*").as_posix(),
        ovp_docker_utils_dir.as_posix()
    )
)


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
    cmd = f"""env L4T_VERSION={L4T_VERSION} \
CUDA_VERSION={CUDA_VERSION} \
PYTHON_VERSION={PYTHON_VERSION} \
LSB_RELEASE={LSB_RELEASE} \
BUILDKIT={int(BUILDKIT)} \
BUILD_WITH_PTY={int(pty)} \
{jetson_exec} build \
--package-dirs '{','.join([ifm3d_package_dirs]+additional_package_dirs)}' --skip-tests all \
--name {repo_name} {' '.join(packages)}"""
    
    tag = f"{repo_name}:r{L4T_VERSION}-cu{CUDA_VERSION.replace('.','')}-cp{PYTHON_VERSION.replace('.','')}"

    print(colorama.Fore.GREEN + f"Running command: {cmd}" + colorama.Style.RESET_ALL)
    ret, output = cli_tee(cmd, wsl=True, pty=True)

    return ret, output, tag




if __name__ == "__main__":
    ...
    # Demonstrate how to build a docker image and push it to a registry using the above functions
    #%%
    parent_dir = Path(__file__).parent
    build_dir = parent_dir/"packages"/"ifm3d"
    tmp_dir = parent_dir/ "tmp"
    dockerfile_path = build_dir/"aggregated.Dockerfile"
    docker_build_output_path = (parent_dir/"ifm3dlab_test_deps.tar").as_posix()


    deployment_example_dir = Path(__file__).parent
    docker_registry_host_relative_to_pc = "localhost"
    docker_registry_port = 5005

    # start a local docker registry
    # docker run -d -p <docker_registry_port>:5000 --name registry registry:latest
    # On windows, you may need to open the port in the firewall for incoming tcp connections

    
    
    repo_name = "ifm3dlab"
    tag_for_vpu = repo_name+":arm64"
    #%%
    output = docker_build(
        build_dir=build_dir,
        dockerfile_path=dockerfile_path.as_posix(),
        tag=tag_for_vpu,
        build_args={
                "BASE_IMAGE": "nvcr.io/nvidia/l4t-base:r32.7.1",
            },
    )
    #%%
    output = prep_image_for_transfer(
        docker_build_output_path= docker_build_output_path,
        tag=tag_for_vpu,
        registry_host=docker_registry_host_relative_to_pc,
        registry_port=docker_registry_port,
    )
    #%%
    get_dusty_nv_repo_if_not_found()
    ret, output, tag = dustynv_build(
        packages = ["docker", "jupyterlab", "ifm3d"],
        repo_name=repo_name,
        L4T_VERSION="32.7.4",
        CUDA_VERSION="10.2",
        PYTHON_VERSION="3.8",
        LSB_RELEASE="18.04",
    )
    #%%
    print(f"pushing to registry with tag: {tag}")
    output = prep_image_for_transfer(
        docker_build_output_path= docker_build_output_path,
        start_tag=tag,
        tag=tag_for_vpu,
        registry_host=docker_registry_host_relative_to_pc,
        registry_port=docker_registry_port,
    )
# %%
