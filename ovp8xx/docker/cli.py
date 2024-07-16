# %%#########################################
# Copyright 2021-present ifm electronic, gmbh
# SPDX-License-Identifier: Apache-2.0
#############################################

import sys
import time
import queue
from subprocess import Popen, PIPE
import threading


def enqueue_stream(stream, queue):
    for line in iter(stream.readline, b''):
        queue.put(line)
    stream.close()


def cli_passthrough(cmd, feedback: dict = {}):

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
        for key in feedback.keys():
            if key in line.decode():
                p.stdin.write(feedback[key].encode())
                p.stdin.flush()
        result.append(line)
    to.join()
    te.join()
    return p.returncode, result

