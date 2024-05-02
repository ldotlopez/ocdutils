#
# OPSNix - One "pedal" studio, Linux version
# Luis López <lopezl@uji.es> @ CENT - UJI
# http://cent.uji.es/


import logging
import os
import sys
import warnings

try:
    import colorama
except ImportError:
    colorama = None

LoggingConfig = dict[str, int | str]

DEFAULT_LOG_LEVEL = logging.DEBUG
ROOT_PACKAGE = __package__.split(".")[0]
DEBUG_ENV_VARIABLE = ROOT_PACKAGE.upper() + "_LOGGING"
LOGGING_CONFIG: LoggingConfig = {ROOT_PACKAGE: DEFAULT_LOG_LEVEL}

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


def infect(config: LoggingConfig = LOGGING_CONFIG):
    global _is_infected

    if _is_infected:
        return

    logging_config: LoggingConfig = {}

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
        logger.setLevel(log_level_value(loglevel))

    _is_infected = True


def log_level_value(level: str | int) -> int:
    if isinstance(level, str):
        return getattr(logging, level.upper())
    else:
        return level


def log_level_name(level: str | int) -> str:
    reallevel = log_level_value(level)
    for x in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
        if reallevel == getattr(logging, x):
            return x

    raise ValueError(level)


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
                yield (name, log_level_value(level))
            except AttributeError:
                warnings.warn(f"Unknow level '{level}' for '{name}'")

    return dict(fn())


def setup_log_level(
    *,
    quiet: int = 0,
    verbose: int = 0,
    root: str | None = None,
):
    if root is None:
        root = ROOT_PACKAGE

    logger = logging.getLogger(root)
    log_level = logger.getEffectiveLevel() - (verbose * 10) + (quiet * 10)
    log_level = max(
        min(log_level, log_level_value("critical")), log_level_value("debug")
    )
    logger.setLevel(log_level)
    # print(log_level_name(logger.getEffectiveLevel()))
