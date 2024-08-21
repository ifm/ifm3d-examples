import logging
import sys

logging.basicConfig(
    format="%(asctime)s:%(filename)-8s:%(lineno)-4d:%(levelname)-8s:%(message)s",
    stream=sys.stdout,
    level=logging.NOTSET,
    datefmt="%y.%m.%d_%H.%M.%S"
)
