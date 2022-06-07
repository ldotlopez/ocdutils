from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class ExifMetadata:
    datetime: datetime


@dataclass
class StatMetadata:
    access: datetime
    modify: datetime
    creation: datetime


@dataclass
class Metadata:
    exif: Optional[ExifMetadata] = None
    stat: Optional[StatMetadata] = None
