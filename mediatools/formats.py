import os
from pathlib import Path

import click

from .lib import filesystem as fs
from .lib import spawn


def remux(
    video: Path, *, format: str, fallback_acodec: str | None = None, overwrite: bool
) -> Path:
    dest = fs.change_file_extension(video, format)

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


@click.command("remux")
@click.option("--format", "-f", default="mp4")
@click.option("--overwrite", is_flag=True, default=False)
@click.option("--rm", is_flag=True, default=False)
@click.option("--verbose", "-v", is_flag=True, default=False)
@click.argument("videos", nargs=-1, required=True, type=Path)
def remux_cmd(
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

        remuxed = remux(v, format=format, fallback_acodec="aac", overwrite=overwrite)
        if verbose:
            print(f"'{v}' -> '{remuxed}'")

        if rm:
            if fs._DRY_RUN:
                print(f"rm -f -- '{v}'")
            else:
                os.unlink(v)


formats_cmd.add_command(remux_cmd)

if __name__ == "__main__":
    formats_cmd()
