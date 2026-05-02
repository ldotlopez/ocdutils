from pathlib import Path
from typing import Any, cast

import ffmpeg
import whisper
from rich.progress import track

from ..consts import FILE_OPERATIONS_CACHE_PATH, RICH_PROGRESS_DISABLED
from ..lib import fslib
from ..lib.clilib import click, print, print_error, rich, target_options
from ..lib.fileopcache import Codecs, FileOperationCache, Validators
from ..lib.hotglue import IFaceLoader


def import_whisper():
    # global whisper
    # if whisper is None:
    #     import whisper
    pass


class WhisperTranscriptions(FileOperationCache):
    DEFAULT_MODEL = "base-v3"
    DEFAULT_LANGUAGE = "en"
    TABLE = "transcriptions_whisper_{model}_{language}_v1"

    def __init__(
        self,
        file: Path = FILE_OPERATIONS_CACHE_PATH,
        model: str = DEFAULT_MODEL,
        language: str = DEFAULT_LANGUAGE,
    ):
        self.TABLE = self.TABLE.format(model=model.replace("-", "_"), language=language)
        super().__init__(file)
        self.model = model
        self.language = language
        self._m: whisper.model.Whisper | None = None

    def _ensure_setup(self) -> None:
        import_whisper()

        if self._m is None:
            self._m = whisper.load_model(self.model)

    def calculate_validator(self, file: Path) -> str:
        return Validators.fast_checksum(file)

    def calculate_value(self, file: Path) -> dict:
        self._ensure_setup()
        tr = transcribe(file, cast(whisper.model.Whisper, self._m), self.language)
        return tr

    def serialize(self, native: Any) -> bytes:
        return Codecs.json_serialize(native)

    def unserialize(self, raw: bytes) -> Any:
        return Codecs.json_unserialize(raw)


def transcribe(
    file: Path, model: whisper.model.Whisper | str = "base", language: str = "en"
) -> dict:
    if isinstance(model, str):
        model = whisper.load_model(model)

    with fslib.temp_dirpath_ctx() as tmpd:
        wav = tmpd / "audio.wav"
        ffmpeg.input(file.as_posix()).output(
            wav.as_posix(), format="wav", acodec="pcm_s16le", ac=1, ar=16000
        ).overwrite_output().run(quiet=True)
        res = model.transcribe(wav.as_posix(), language=language)

        return res


@click.group
def audio_cmd():
    pass


@audio_cmd.command
@click.option("-m", "--model", type=str, default=WhisperTranscriptions.DEFAULT_MODEL)
@click.option(
    "-l",
    "--language",
    type=str,
    default=WhisperTranscriptions.DEFAULT_LANGUAGE,
)
@target_options
def transcribe_cmd(
    targets: list[Path], recursive: bool, pre_scan: bool, model: str, language: str
):
    backends = IFaceLoader(base_module="..plugins", scan=True)

    audios = fslib.iter_files(*targets, recursive=recursive)
    audios = (
        x
        for x in audios
        if fslib.file_matches_mime(x, "audio/*") or x.suffix.lower() in [".m4a"]
    )
    if pre_scan:
        audios = list(audios)  # type: ignore[assignment]

    transcriptor = WhisperTranscriptions(model=model, language=language)
    for audio in track(audios, disable=RICH_PROGRESS_DISABLED):
        print(f"'{audio}': starting transcription, may take a while")
        tr = transcriptor.get(audio.resolve())
        print(f"'{audio}': len={len(tr['text'])}, segments={len(tr['segments'])}")
        print(tr["text"])
