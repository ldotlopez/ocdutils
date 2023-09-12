import os
from pathlib import Path

import click

from .lib import filesystem as fs
from .lib import spawn


def heic2jpg(heic: Path, overwrite: bool) -> Path:
    dest = fs.change_file_extension(heic, "jpg")
    temp = fs.temp_filename(dest)

    cmdl = ["convert", "-auto-orient", heic.as_posix(), temp.as_posix()]
    if fs._DRY_RUN:
        print(" ".join(cmdl))
    else:
        spawn.run(*cmdl)

    fs.clone_exif(heic, temp)
    fs.clone_stat(heic, temp)
    return fs.safe_mv(temp, dest, overwrite=overwrite)


def mp4ize(video: Path, *, fallback_acodec: str | None = None, overwrite: bool) -> Path:
    dest = fs.change_file_extension(video, "mp4")

    temp = fs.temp_filename(dest)

    acodecs = ["copy"]
    if fallback_acodec:
        acodecs.append(fallback_acodec)

    ffmpeg_ok = False
    for idx, ca in enumerate(acodecs):
        try:
            cmdl = [
                "ffmpeg",
                "-loglevel",
                "warning",
                "-y",
                "-i",
                video.as_posix(),
                "-c:v",
                "copy",
                "-c:a",
                ca,
                temp.as_posix(),
            ]
            if fs._DRY_RUN:
                print(" ".join(cmdl))
            else:
                spawn.run(*cmdl)

            ffmpeg_ok = True
            break

        except spawn.ProcessFailure:
            if temp.exists():
                temp.unlink()

            if idx + 1 == len(acodecs):
                raise

    if not ffmpeg_ok:
        raise SystemError()

    fs.clone_stat(video, temp)
    fs.clone_exif(video, temp)
    return fs.safe_mv(temp, dest, overwrite=overwrite)


@click.group("formats")
def formats_cmd():
    pass


@click.command("mp4ize")
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--rm", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("videos", nargs=-1, required=True, type=Path)
def mp4ize_cmd(
    videos,
    *,
    format: str = "mp4",
    overwrite: bool = False,
    rm: bool = False,
    verbose: bool = False,
):
    for v in videos:
        if not v.is_file():
            click.echo(f"{click.format_filename(v)}: not a file", err=True)
            continue

        remuxed = mp4ize(v, fallback_acodec="aac", overwrite=overwrite)
        if verbose:
            print(f"'{v}' -> '{remuxed}'")

        if rm:
            if fs._DRY_RUN:
                print(f"rm -f -- '{v}'")
            else:
                os.unlink(v)


@click.command("jpgize")
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--rm", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("images", nargs=-1, required=True, type=Path)
def jpgize_cmd(
    images,
    *,
    overwrite: bool = False,
    rm: bool = False,
    verbose: bool = False,
):
    supported_mime = {"image/heic": heic2jpg}

    for img in images:
        if not img.is_file():
            click.echo(f"{click.format_filename(img)}: not a file", err=True)
            continue

        mime = fs.file_mime(img)
        if mime not in supported_mime:
            click.echo(f"{click.format_filename(img)}: unsupported format", err=True)

        supported_mime[mime](img, overwrite=overwrite)


formats_cmd.add_command(mp4ize_cmd)
formats_cmd.add_command(jpgize_cmd)

if __name__ == "__main__":
    formats_cmd()
