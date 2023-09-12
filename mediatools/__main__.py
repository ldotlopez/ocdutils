import logging

from . import cli

_LOGGER = logging.getLogger(__name__)
_LOGGER.setLevel(logging.DEBUG)

if __name__ == "__main__":
    cli.main()
