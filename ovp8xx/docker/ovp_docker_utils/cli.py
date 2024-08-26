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

try:
    import ovp_docker_utils.logs
except ImportError:
    import logs

logger = logging.getLogger(__name__)

def enqueue_stream(stream: io.BufferedReader , queue):
    # https://stackoverflow.com/a/57084403/10861094
    for line in iter(stream.read1, b''):
        queue.put(line)
    stream.close()

wsl_prefix = 'wsl -e'
pty_wrapper_prefix = 'python3 -u -c "import pty, sys; pty.spawn(sys.argv[1:])" /bin/bash -c'

color_native, color_wsl = colorama.Fore.LIGHTCYAN_EX, colorama.Fore.CYAN
color_from_ctx = lambda wsl: {True: color_wsl, False: color_native}[wsl]
colorize = lambda x, ctx = color_native: f"{color_from_ctx(ctx)}{x}{colorama.Style.RESET_ALL}"

def cli_tee(
    cmd:str,
    wsl=False,
    pty=False,
    feedback: dict = {},
    
    show_i = True,
    colorful_i = True,

    show_e= True,
    show_o= True,

    cache_e = True,
    cache_o = True,

    t_refresh = 0.01
    ):

    pty = pty and (os.name!='nt' or (os.name=='nt' and wsl))
    wsl = wsl and os.name == 'nt'

    if pty:
        cmd = cmd.replace('"', '\\"')
        cmd = f'{pty_wrapper_prefix} "{cmd}"'
    if wsl:
        cmd = f'{wsl_prefix} {cmd}'

    if show_i:
        ctx_desc = {True:"in WSL",False: "locally"}[wsl]
        msg = f"Running {ctx_desc}: "
        if colorful_i:
            msg += colorize(cmd,wsl)
        else:
            msg += cmd
        logger.info(msg)

    stdin = PIPE if feedback!={} else None
    stdout = PIPE if show_o or cache_o else None
    stderr = PIPE if show_e or cache_e else None

    qo = None
    cached_o = []
    qe = None
    cached_e = []
    p = Popen(
        cmd,
        stdin=stdin,
        stdout=stdout,
        stderr=stderr,
        shell=True,
    )
    if stdout:
        qo = queue.Queue()
        to = threading.Thread(target=enqueue_stream, args=(p.stdout, qo))
        to.start()
    if stderr:
        qe = queue.Queue()
        te = threading.Thread(target=enqueue_stream, args=(p.stderr, qe))
        te.start()
    running = True
    while running:
        if qe and not qe.empty():
            line = qe.get()
            if show_e:
                sys.stderr.write(line.decode())
                sys.stderr.flush()
            cached_e.append(line)
        if qo and not qo.empty():
            line = qo.get()
            if show_o:
                sys.stdout.write(line.decode())
                sys.stdout.flush()
            cached_o.append(line)
            for key in feedback.keys():
                if key in line.decode():
                    p.stdin.write(feedback[key].encode())
                    p.stdin.flush()
        running = p.poll() is None 
        time.sleep(t_refresh)


    if show_i:
        logger.info(f"Returned: {colorama.Style.RESET_ALL}{p.returncode}")

    if stderr:
        p.stderr.close()
    if stdout:
        p.stdout.close()
    p.terminate
    p.wait()
    if stderr:
        te.join()
    if stdout:
        to.join()
            
    return p.returncode, b"".join(cached_o), b"".join(cached_e)


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
    ...
    #%%
    # from pathlib import Path
    # pipe_path = Path(__file__).parent / "ssh_pipe.py"
    # python = sys.executable
    # r, o, e = cli_tee(
    #     cmd = f'{python} {pipe_path} /home/usdagest/dev/ifm3d-examples/ovp8xx/docker/ovp_docker_utils/tmp/l4t-ifm3dlab-docke-jupyt-ovp_r-ifm3d.0.0.0-arm64.tar',
    #     )
    #%%
    r, o, e = cli_tee(
        "ls -la",
    )

# %%
