import logging

from termcolor import colored

from conf import config


def makeStatus():
    return f"{'⚠️' if config.run_for_test else '' }🏠:{colored(config.status['total'],'blue')} 🌀:{colored(config.status['updated'],'blue')} ✅:{colored(config.status['success'],'green')} 🚫:{colored(config.status['failed'],'red')}] "


logging.basicConfig(format="[%(asctime)s]%(message)s", level=logging.INFO)
loger = logging.getLogger(config.name)


def info(txt):
    return loger.info(f"{ makeStatus()} {colored(txt, 'blue')}")


def success(txt):
    return loger.info(f"{makeStatus()} {colored(txt, 'green')}")


def warning(txt):
    return loger.info(f"{makeStatus()} {colored(txt, 'yellow')}")


def error(txt):
    return loger.info(f"{makeStatus()} {colored(txt, 'red')}")
