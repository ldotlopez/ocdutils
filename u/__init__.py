import logging

from dotenv import load_dotenv
from rich.logging import RichHandler

# logging.basicConfig()
LOGGING_FORMAT = "[%(name)s] %(message)s"
logging.basicConfig(level="NOTSET", format=LOGGING_FORMAT, handlers=[RichHandler()])

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)
load_dotenv()
