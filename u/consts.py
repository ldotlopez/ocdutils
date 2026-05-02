import os

import platformdirs

PROJECT = "hkos"
FILE_OPERATIONS_CACHE_PATH = platformdirs.user_cache_path(f"{PROJECT}/opcache.sqlite")
RICH_PROGRESS_DISABLED = os.environ.get("RICH_PROGRESS_ENABLED", "") in (
    "0",
    "no",
    "",
)
