import os

import platformdirs

PROJECT = "hkos"
FILE_OPERATIONS_CACHE_PATH = platformdirs.user_cache_path(f"{PROJECT}/opcache.sqlite")
RICH_PROGRESS_ENABLED = os.environ.get("RICH_PROGRESS_ENABLED", "") not in (
    "0",
    "no",
    "",
)
