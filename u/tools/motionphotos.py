from __future__ import annotations

import sys
from pathlib import Path

from ..lib import fslib
from ..lib.clilib import click, print_error, target_options
from .sidecars import filter_group_set_by_extensions, scan_for_sidecars

_MOTIONPHOTO_MARKER = b"MotionPhoto_Data"

# --- Core clasess -- #


class MotionPhotoBytes:
    # @classmethod
    # def fromfile(cls, filepath: str, *args, **kwargs) -> MotionPhotoBytes:
    #     with open(filepath, "rb") as fh:
    #         return cls(fh.read(), *args, **kwargs)

    def __init__(self, buff: bytes, marker: bytes = _MOTIONPHOTO_MARKER):
        self.marker = marker
        idx = buff.find(self.marker)

        self.image: memoryview
        self.video: memoryview | None

        if idx >= 0:
            self.image = memoryview(buff[0:idx])
            self.video = memoryview(buff[idx + len(self.marker) :])
        else:
            self.image = memoryview(buff[:])
            self.video = None

    @property
    def has_video(self) -> bool:
        return self.video is not None

    def insert_video(self, buff: bytes) -> None:
        self.video = memoryview(buff)

    def drop_video(self) -> None:
        self.video = None

    @property
    def data(self) -> bytes:
        if self.has_video:
            return bytes(self.image) + self.marker + bytes(self.video)  # type: ignore[arg-type]
        else:
            return bytes(self.image)


class MotionPhoto(MotionPhotoBytes):
    def __init__(self, filepath: str | Path):
        if isinstance(filepath, str):
            filepath = Path(filepath)

        return super().__init__(filepath.read_bytes())

    def insert_video(self, filepath: str | Path):  # type: ignore[override]
        if isinstance(filepath, str):
            filepath = Path(filepath)

        if not fslib.file_matches_mime(filepath, "video/*"):
            raise ValueError(filepath)

        super().insert_video(filepath.read_bytes())

    def save(self, filepath: str | Path):
        if isinstance(filepath, str):
            filepath = Path(filepath)

        if filepath.suffix.lower() != ".jpg":
            raise ValueError(filepath)

        filepath.write_bytes(self.data)


# --- High level funcions --- #


def check(file: Path) -> bool:
    return MotionPhoto(file).has_video


def join(image: Path, video: Path, output: Path | None = None) -> Path:
    mp = MotionPhoto(image)
    mp.insert_video(video)

    output = output or fslib.temp_filepath(suffix=".jpg")
    mp.save(output.as_posix())

    fslib.clone_stat(image, output)
    return output


def split(
    input: Path, image: Path | None = None, video: Path | None = None
) -> tuple[Path, Path | None]:
    mp = MotionPhoto(input)

    image = image or fslib.temp_filepath(suffix=".jpg")
    image.write_bytes(mp.image)
    fslib.clone_stat(input, image)

    if mp.has_video:
        video = video or fslib.temp_filepath(suffix=".mp4")
        video.write_bytes(mp.video)  # type: ignore[arg-type]
        fslib.clone_stat(input, video)

    else:
        video = None

    return image, video


def drop(input: Path, output: Path | None = None) -> Path:
    output = output or fslib.temp_filepath(suffix=".jpg")
    mp = MotionPhoto(input)
    mp.drop_video()
    mp.save(output)

    fslib.clone_stat(input, output)
    return output


# --- Click commands --- #


@click.group
def motionphotos_cmd():
    """Tools for handling motionphotos."""
    pass


@motionphotos_cmd.command("check")
@click.argument("image", type=Path)
def is_motionphoto_cmd(image: Path) -> int:
    """Check if a file is a motionphoto."""

    if check(image):
        print(f"'{image}': is a motionphoto")
        sys.exit(0)
    else:
        print(f"'{image}': is NOT a motionphoto")
        sys.exit(1)


@motionphotos_cmd.command("join")
@click.option("--image", "-i", type=Path, required=True)
@click.option("--video", "-v", type=Path, required=True)
@click.option("--overwrite", is_flag=True, default=False)
@click.option("-o", "--output", type=Path, required=True)
@click.option(
    "--rm",
    "-d",
    "delete_video",
    is_flag=True,
    default=False,
    help="Delete original video",
)
def join_cmd(
    image: Path, video: Path, output: Path, overwrite: bool, delete_video: bool
):
    """Merge image and video into a motionphoto."""
    temp = join(
        image=image,
        video=video,
    )
    fslib.safe_mv(temp, output, overwrite=overwrite)
    if delete_video:
        video.unlink()


@motionphotos_cmd.command("split")
@click.option("--mp", type=Path, required=True)
@click.option("--image", "-i", type=Path, required=True)
@click.option("--video", "-v", type=Path, required=True)
@click.option("--overwrite", is_flag=True, default=False)
def split_cmd(mp: Path, image: Path, video: Path, overwrite: bool):
    """Split a motionphoto in a image and a video."""
    tmp_img, tmp_vid = split(mp)

    fslib.safe_mv(tmp_img, image, overwrite=overwrite)
    if tmp_vid:
        fslib.safe_mv(tmp_vid, video, overwrite=overwrite)


@motionphotos_cmd.command("strip")
@click.option("--overwrite", is_flag=True, default=False)
@click.option("-o", "--output", type=Path)
@click.argument("input", type=Path)
def strip_cmd(input: Path, output: Path, overwrite: bool):
    """Strip video from a motionphoto."""

    output = output or input
    if input == output and not overwrite:
        print_error(f"'{input}': you have to use --overwrite or --output")
        sys.exit(255)

    temp = drop(input)
    fslib.safe_mv(temp, output, overwrite=overwrite)


@motionphotos_cmd.command
@click.option(
    "--keep-video",
    "keep_video",
    is_flag=True,
    help="Delete original video",
)
@target_options
def merge_cmd(targets: list[Path], recursive: bool, pre_scan: bool, keep_video: bool):
    """Merge matching images and videos into motionphotos."""
    sidecars = scan_for_sidecars(fslib.iter_files(*targets, recursive=recursive))
    images_and_videos = filter_group_set_by_extensions(
        sidecars, extensions=["jpg", "mp4"]
    )

    for _, pairs in images_and_videos:
        by_ext = dict(pairs)
        image = by_ext["jpg"]
        video = by_ext["mp4"]

        temp = join(image=image, video=video)
        fslib.safe_mv(temp, image, overwrite=True)
        if not keep_video:
            video.unlink()
