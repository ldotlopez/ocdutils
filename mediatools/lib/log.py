#
# OPSNix - One "pedal" studio, Linux version
# Luis López <lopezl@uji.es> @ CENT - UJI
# http://cent.uji.es/


import logging
import os
import sys
import warnings
from typing import Dict, Union

try:
    import colorama
except ImportError:
    colorama = None


ROOT_PACKAGE = __package__.split(".")[0]
DEBUG_ENV_VARIABLE = ROOT_PACKAGE.upper() + "_DEBUG"
LOGGING_CONFIG = {ROOT_PACKAGE: logging.DEBUG}

_is_infected = False


class LogFormater(logging.Formatter):
    MAX_NAME_LEN = 10
    LEVEL_ABBRS = {
        "CRITICAL": "CRT",
        "ERROR": "ERR",
        "WARNING": "WRN",
        "INFO": "NFO",
        "DEBUG": "DBG",
    }

    if colorama:
        COLOR_MAP = {
            logging.DEBUG: colorama.Fore.CYAN,
            logging.INFO: colorama.Fore.GREEN,
            logging.WARNING: colorama.Fore.YELLOW,
            logging.ERROR: colorama.Fore.RED,
            logging.CRITICAL: colorama.Back.RED,
        }
    else:
        COLOR_MAP = {}

    def format(self, record):
        record.levelname = self.LEVEL_ABBRS[record.levelname]

        # if "." in record.name:
        #     record.name = "." + record.name.split(".")[-1]
        # if len(record.name) < self.MAX_NAME_LEN:
        #     record.name = record.name.ljust(self.MAX_NAME_LEN)
        # elif len(record.name) > self.MAX_NAME_LEN:
        #     idx = self.MAX_NAME_LEN - 3
        #     record.name = ". …" + record.name[-idx:]

        output = super().format(record)
        color = self.COLOR_MAP.get(record.levelno)
        if color:
            output = f"{color}{output}{colorama.Style.RESET_ALL}"

        return output


def infect(config=LOGGING_CONFIG):
    global _is_infected

    if _is_infected:
        return

    logging_config = {}

    if env_debug_config := os.environ.get(DEBUG_ENV_VARIABLE, ""):
        logging_config.update(parse_log_str(env_debug_config))
    else:
        logging_config.update(config)

    formatter = LogFormater(
        fmt="%(asctime)s %(levelname)s [%(threadName)s] %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.addHandler(handler)

    for logname, loglevel in logging_config.items():
        logger = root if logname == "*" else logging.getLogger(logname)
        logger.setLevel(get_log_level(loglevel))

    _is_infected = True


def get_log_level(level: str | int) -> int:
    if isinstance(level, str):
        return getattr(logging, level.upper())
    else:
        return level


def parse_log_str(s: str) -> dict[str, int]:
    def fn():
        if not s:
            return

        components = s.split(",")
        for comp in components:
            parts = comp.split(":", 1)
            if len(parts) == 1:
                name, level = "*", parts[0]
            else:
                name, level = parts
            level = level.lower()

            try:
                yield (name, get_log_level(level))
            except AttributeError:
                warnings.warn(f"Unknow level '{level}' for '{name}'")

    return dict(fn())
