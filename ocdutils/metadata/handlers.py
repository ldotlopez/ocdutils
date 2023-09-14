import abc
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path

import piexif

from .types import ExifMetadata, Metadata, StatMetadata

_LOGGER = logging.getLogger(__name__)


class _BaseException(Exception):
    pass


class BackendMissingError(_BaseException):
    pass


class MetadataReadError(_BaseException):
    pass


class MetadataNotFoundError(_BaseException):
    pass


class _BaseHandler:
    def __init__(self, filepath: Path):
        self.filepath = filepath.absolute()

    @abc.abstractmethod
    def get(self) -> Metadata:
        raise NotImplementedError()

    @abc.abstractmethod
    def set(self, metadata: Metadata):
        raise NotImplementedError()


# class ExifHandler(_BaseHandler):
#     def __init__(self, filepath: Path):
#         super().__init__(filepath)

#         BackendClass = self._get_backend(self.filepath)
#         self._backend = BackendClass()

#     def get(self) -> Any:
#         return self._backend.read(self.filepath)

#     def set(self, metadata: Any):
#         self._backend.write(self.filepath, metadata)

#     def _get_backend(self, filepath: Path):
#         tbl = {
#             "jpeg": ExifJpegBackend,
#             "jpg": ExifJpegBackend,
#             "m4v": ExifVideoBackend,
#             "mov": ExifVideoBackend,
#             "mp4": ExifVideoBackend,
#         }

#         ext = filepath.suffix.lstrip(".").lower()
#         try:
#             return tbl[ext]
#         except KeyError as e:
#             raise BackendMissingError(filepath) from e


def ExifHandler(filepath: Path, *args, **kwargs):
    tbl = {
        "jpeg": ExifJpegBackend,
        "jpg": ExifJpegBackend,
        "m4v": ExifVideoBackend,
        "mov": ExifVideoBackend,
        "mp4": ExifVideoBackend,
    }

    ext = filepath.suffix.lstrip(".").lower()
    try:
        return tbl[ext](filepath, *args, **kwargs)
    except KeyError as e:
        raise BackendMissingError(filepath) from e

    return


class ExifJpegBackend(_BaseHandler):
    def __init__(
        self,
        *args,
        ignore_original_digitized_missmatch=False,
        overwrite_original_datetime=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.ignore_original_digitized_diff = ignore_original_digitized_missmatch
        self.overwrite_original_datetime = overwrite_original_datetime

    def get(self) -> Metadata:
        def _get_dt(exifdata, datetime_tag, offset_tag):
            dtstr = exif["Exif"].get(datetime_tag).decode("ascii")
            if dtstr is None:
                return None

            dt = datetime.strptime(dtstr, "%Y:%m:%d %H:%M:%S")

            if dtstr.find(" 24:") > 0:
                dtstr = dtstr.replace(" 24:", " 00:")
                dt += timedelta(days=1)

            if offsetstr := exif["Exif"].get(offset_tag):
                offset = str(offsetstr.decode("ascii"))
                dt += timedelta(seconds=offset)

            return dt

        try:
            exif = piexif.load(self.filepath.as_posix())
        except piexif.InvalidImageDataError as e:
            raise MetadataReadError() from e

        tags = [
            (piexif.ExifIFD.DateTimeOriginal, piexif.ExifIFD.OffsetTimeOriginal),
            (piexif.ExifIFD.DateTimeDigitized, piexif.ExifIFD.OffsetTimeDigitized),
        ]

        dt_original, dt_digitalized = (
            _get_dt(exif, dt_tag, offset_tag) for (dt_tag, offset_tag) in tags
        )

        if not dt_original and not dt_digitalized:
            raise MetadataNotFoundError("exif tags not found")

        if dt_original != dt_digitalized:
            missmatch = f"original:{dt_original} != digitized:{dt_digitalized}"
            if self.ignore_original_digitized_diff:
                _LOGGER.warning(
                    f"{self.filepath}: ignoring original and digitized missmatch "
                    f"({missmatch})"
                )
            else:
                raise ValueError(missmatch)

        return Metadata(ExifMetadata(datetime=dt_original or dt_digitalized))

    def set(self, metadata: Metadata):
        if not metadata.exif:
            _LOGGER.warning("Missing exif metadata, nothing to do")
            raise MetadataNotFoundError()

        try:
            exifdata = piexif.load(self.filepath.as_posix())
        except piexif.InvalidImageDataError as e:
            raise MetadataReadError() from e

        if "Exif" not in exifdata:
            exifdata["Exif"] = {}

        dtstr = datetime.strftime(metadata.exif.datetime, "%Y:%m:%d %H:%M:%S")
        dtbytes = dtstr.encode("ascii")

        exifdata["Exif"][piexif.ExifIFD.DateTimeDigitized] = dtbytes
        if self.overwrite_original_datetime:
            exifdata["Exif"][piexif.ExifIFD.DateTimeOriginal] = dtbytes

        for tag in [
            piexif.ExifIFD.OffsetTime,
            piexif.ExifIFD.OffsetTimeOriginal,
            piexif.ExifIFD.OffsetTimeDigitized,
        ]:
            try:
                del exifdata["Exif"][tag]
            except KeyError:
                pass

        piexif.insert(piexif.dump(exifdata), self.filepath.as_posix())


class ExifVideoBackend(_BaseHandler):
    pass


class StatHandler(_BaseHandler):
    def get(self) -> Metadata:
        st = self.filepath.stat()

        return Metadata(
            stat=StatMetadata(
                access=datetime.fromtimestamp(st.st_atime),
                modify=datetime.fromtimestamp(st.st_mtime),
                creation=datetime.fromtimestamp(st.st_ctime),
            )
        )

    def set(self, metadata: Metadata):
        st = metadata.stat
        os.utime(
            self.filepath.as_posix(),
            (st.access.timestamp(), st.modify.timestamp()),
        )


def Factory(name: str, *args, **kwargs) -> _BaseHandler:
    if name == "exif":
        return ExifHandler(*args, **kwargs)
    elif name == "stat":
        return StatHandler(*args, **kwargs)
    else:
        raise NameError(name)
