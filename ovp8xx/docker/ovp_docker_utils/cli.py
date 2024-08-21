# %%#########################################
# Copyright 2024-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import sys
import os
import time
import queue
from subprocess import Popen, PIPE
import threading
import re
import logging


logger = logging.getLogger(__name__)

def enqueue_stream(stream, queue):
    # https://stackoverflow.com/a/57084403/10861094
    for line in iter(stream.readline, b''):
        queue.put(line)
    stream.close()

wsl_prefix = 'wsl -e' if os.name == "nt" else ""

pty_wrapper_prefix = 'python3 -u -c "import pty, sys; pty.spawn(sys.argv[1:])" /bin/bash -c'

def cli_tee(cmd:str, wsl=False, pty=False, feedback: dict = {}, verbose = False, suppress = False):
    """
    Run a command in a shell. Passes the output to the console.

    Args:
        cmd (str): Command to run
        wsl (bool, optional): Run the command in WSL. Defaults to False.
        pty (bool, optional): Run the command in a pty. Defaults to False.
        feedback (dict, optional): A dictionary of feedback strings and responses. Defaults to {}.

    Returns:
        tuple: (result, output)
    """

    if pty:
        cmd = cmd.replace('"', '\\"')
        cmd = f'{pty_wrapper_prefix} "{cmd}"'
    if wsl:
        cmd = f'{wsl_prefix} {cmd}'
    if verbose:
        print(f"Running command: {cmd}")

    p = Popen(
        cmd,
        stdin=PIPE,
        stdout=PIPE,
        stderr=PIPE,
        shell=True,
    )
    qo = queue.Queue()
    to = threading.Thread(target=enqueue_stream, args=(p.stdout, qo))
    te = threading.Thread(target=enqueue_stream, args=(p.stderr, qo))
    te.start()
    to.start()

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
        to.join()
        te.join()
    except KeyboardInterrupt:
        p.terminate()
        p.wait()
        to.join()
        te.join()
        raise KeyboardInterrupt
    return p.returncode, result


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


