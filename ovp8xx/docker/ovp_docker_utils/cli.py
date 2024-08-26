# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import sys
import os
import time
import queue
from subprocess import Popen, PIPE
import io
import threading
import re
import logging

import colorama

logger = logging.getLogger(__name__)

def enqueue_stream(stream: io.BufferedReader , queue):
    # https://stackoverflow.com/a/57084403/10861094
    for line in iter(stream.read1, b''):
        # print(line)
        queue.put(line)
    stream.close()

wsl_prefix = 'wsl -e'

pty_wrapper_prefix = 'python3 -u -c "import pty, sys; pty.spawn(sys.argv[1:])" /bin/bash -c'

def cli_tee(cmd:str, wsl=False, pty=False, feedback: dict = {}, verbose = False, pretty = True, suppress = False, ignore_stderr = True):
    """
    """

    pty = pty and (os.name!='nt' or (os.name=='nt' and wsl))
    wsl = wsl and os.name == 'nt'

    if pty:
        cmd = cmd.replace('"', '\\"')
        cmd = f'{pty_wrapper_prefix} "{cmd}"'
    if wsl:
        cmd = f'{wsl_prefix} {cmd}'
    if verbose:
        ctx = {True:"in WSL",False: "locally"}[wsl]
        if pretty:
            style = {True: colorama.Fore.CYAN, False: colorama.Fore.LIGHTCYAN_EX}[wsl]
            msg = f'Running {ctx}:{style} {cmd}' + colorama.Style.RESET_ALL
        else:
            msg = f'Running {ctx}: {cmd}'
        logger.info(msg)

    p = Popen(
        cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        shell=True,
    )
    qo = queue.Queue()
    to = threading.Thread(target=enqueue_stream, args=(p.stdout, qo))
    to.start()
    if not ignore_stderr:
        te = threading.Thread(target=enqueue_stream, args=(p.stderr, qo))
        te.start()

    result = []
    try:
        while True:
            if qo.empty():
                if p.poll() is not None:
                    break
                time.sleep(0.05)
                continue
            line = qo.get()
            if not suppress:
                if type(line) == str:
                    sys.stdout.write(line)
                    sys.stdout.flush()
                else:
                    sys.stdout.write(line.decode())
                    sys.stdout.flush()
                for key in feedback.keys():
                    if key in line.decode():
                        p.stdin.write(feedback[key].encode())
                        p.stdin.flush()
            result.append(line)
        if verbose:
            logger.info(f"Return code: {p.returncode}")
        p.stdout.close()
        p.stderr.close()
        to.join()
        if not ignore_stderr:
            te.join()
    except KeyboardInterrupt:
        p.terminate()
        p.wait()
        to.join()
        if not ignore_stderr:
            te.join()
        raise KeyboardInterrupt
    return p.returncode, b"".join(result)


def convert_nt_to_wsl(path: str):
    """
    Substitute absolute windows path with absolute wsl path
    <drive_letter>:/ becomes /mnt/<drive_letter_lower_case>/
    """
    drive_letter = re.match(r"([A-Za-z]):", path)
    if drive_letter:
        path = re.sub(r"([A-Za-z]):", f"/mnt/{drive_letter.group(1).lower()}", path)
    path = path.replace("\\", "/")
    return path


if __name__=="__main__":
    from pathlib import Path
    pipe_path = Path(__file__).parent / "ssh_pipe.py"
    python = sys.executable
    cli_tee(f'{python} {pipe_path} /home/usdagest/dev/ifm3d-examples/ovp8xx/docker/ovp_docker_utils/tmp/l4t-ifm3dlab-docke-jupyt-ovp_r-ifm3d.0.0.0-arm64.tar', verbose=True, pty=True)