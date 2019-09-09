import os
import time
from contextlib import contextmanager

from conf import config
from log import info


@contextmanager
def check_times(level=3):
    timeStart = time.time()
    yield
    info(f"cost times: {round(time.time()-timeStart,level)}s")


def checkCount(func):
    def checker(*args, **kwargs):
        try:
            res = func(*args, **kwargs)
            config.status["success"] += 1
            return res
        except Exception:
            config.status["failed"] += 1
            raise

    return checker(func)


def addsucess():
    config.status["success"] += 1


def addfailed():
    config.status["failed"] += 1


def addtotal():
    config.status["total"] += 1


def addupdate():
    config.status["updated"] += 1


def check_path(path):
    return os.path.exists(path)


def init_path(path):
    if not check_path(path):
        os.makedirs(path)
