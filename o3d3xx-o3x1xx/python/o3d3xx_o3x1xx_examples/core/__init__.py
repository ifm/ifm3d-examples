# -*- coding: utf-8 -*-
import os


def set_noProxy(ip):
    os.environ["NO_PROXY"] = ip
    return
