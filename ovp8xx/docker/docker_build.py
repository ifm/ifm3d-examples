# %%#########################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################
import sys
import logging
import os
from pathlib import Path
import time
import queue
from subprocess import Popen, PIPE
import threading

##

logger = logging.getLogger()

logging.basicConfig()


def convert_nt_to_wsl(path: str):
    return (str(path).replace("\\", "/").replace("C:/", "/mnt/c/").replace("c:/", "/mnt/c/"))


os.environ["PYTHONUNBUFFERED"]="1"

def enqueue_stream(stream, queue):
    for line in iter(stream.readline ,b''):
        queue.put(line)
    stream.close()

def cli_passthrough(cmd):

    p = Popen(
        cmd,
        stdout=PIPE,
        stderr=PIPE,
        # bufsize=-1,
        shell=True,
    )
    qo = queue.Queue()
    to = threading.Thread(target=enqueue_stream, args=(p.stdout, qo))
    te = threading.Thread(target=enqueue_stream, args=(p.stderr, qo))
    te.start()
    to.start()

    result = []
    while True:
        if qo.empty():
            if p.poll() is not None:
                break
            time.sleep(0.05)
            continue
        line = qo.get()        
        if type(line) == str:
            sys.stdout.write(line)
            sys.stdout.flush()
        else:
            sys.stdout.write(line.decode())
            sys.stdout.flush()
        result.append(line)
    to.join()
    te.join()
    return result


def docker_build(
    build_dir=".",
    dockerfile_path: str = "Dockerfile",
    docker_build_output_path: str = "",
    repo_name: str = "example_build",
    build_args: dict = {},
    os_target: str = "linux",
    arch: str = "arm64",
    registry_host: str = None,
    registry_port=5000,
    target: str = "",
    Additional_build_params: str = "--progress=plain",
    timeout=10000,
):
    """
    This function builds a docker container.

    Parameters
    ----------
    docker_build : str
        simplified string representation of the docker build command
    """
    if "ipykernel" in sys.modules:
        logger.info(
            """...\n...Output from container build may not be available while using ipython...\n...If desired, try running the command in a separate terminal: """)

    logger.info(f"Attempting docker build")

    build_dir = Path(build_dir).resolve().as_posix()
    if os.name == "nt" and os_target != "windows":
        build_dir = convert_nt_to_wsl(build_dir)
        dockerfile_path = convert_nt_to_wsl(Path(dockerfile_path).resolve().as_posix())
        if docker_build_output_path:
            docker_build_output_path = convert_nt_to_wsl(
                docker_build_output_path)
    tag = repo_name
    if registry_host:
        registry_tag = f"{registry_host}:{registry_port}/{tag}"

    build_arg_str = " ".join(
            [f"--build-arg=\"{key}={value}\"" for key, value in build_args.items()])
    
    target_str = ""
    if target:
        target_str = f"--target {target}"

    wsl_prefix = 'wsl python3 -u -c "import pty, sys; pty.spawn(sys.argv[1:])"' if os.name == "nt" and os_target != "windows" else ""

    cmds = []
    if repo_name:
        cmds = [
            f'{wsl_prefix} docker buildx build {build_arg_str} {target_str} --platform {os_target}/{arch} -f "{dockerfile_path}" {Additional_build_params} {build_dir} -t {tag}'
        ]
        if docker_build_output_path:
            cmds.append(
                f'docker save  {tag} > {docker_build_output_path}')
    elif docker_build_output_path:
        cmds = [
            f'{wsl_prefix} docker buildx build {build_arg_str} {target_str} --platform {os_target}/{arch} -f \'{dockerfile_path}\' {Additional_build_params} . -o "type=tar,dest={docker_build_output_path}"'
        ]
    if registry_host and repo_name:
        cmds.append(
            f'{wsl_prefix} docker tag {tag} {registry_tag}'
        )
        cmds.append(
            f'{wsl_prefix} docker push {registry_host}:{registry_port}/{tag}')

    for cmd in cmds:
        print(f"Running command: {cmd}")
        result = cli_passthrough(cmd)

build_dir = Path(__file__).parent


if __name__ == "__main__":


    BUILD_DIR = Path(__file__).parent.absolute()
    os.chdir(BUILD_DIR)
    tmp_dir = BUILD_DIR / "tmp"

    deployment_example_dir = Path(__file__).parent
    docker_registry_host_relative_to_pc = "localhost"
    docker_registry_port = 5005

    # start a local docker registry
    # docker run -d -p <docker_registry_port>:5000 --name registry registry:latest
    # On windows, you may need to open the port in the firewall for incoming tcp connections

    docker_build(
        build_dir=BUILD_DIR,
        dockerfile_path=str(BUILD_DIR / "python" / "python_deps.Dockerfile"),
        repo_name="ovp_python_deps:arm64",
        docker_build_output_path= str(tmp_dir/"docker_python_deps.tar"),
        registry_host=docker_registry_host_relative_to_pc,
        registry_port=docker_registry_port
    )
    docker_build(
        build_dir=BUILD_DIR,
        dockerfile_path=str(BUILD_DIR / "win64.Dockerfile"),
        repo_name="windows_example:arm64",
        os_target="windows",
        arch="amd64",
        docker_build_output_path= str(tmp_dir/"windows_example.tar"),
        registry_host=docker_registry_host_relative_to_pc,
        registry_port=docker_registry_port
    )
# %%
