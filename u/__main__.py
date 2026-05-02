import rich_click as click

from .tools.imghash import find_duplicates_cmd, img_hash_cmd
from .tools.mediaformats import jpgize_cmd, mp4ize_cmd
from .tools.motionphotos import motionphotos_cmd
from .tools.renamers import rename_cmd
from .tools.sidecars import sidecars_cmd

# from .tools.audio import audio_cmd


@click.group
def main():
    pass


# main.add_command(audio_cmd, name="audio")
main.add_command(find_duplicates_cmd, name="img-duplicates")
main.add_command(img_hash_cmd, name="img-hash")
main.add_command(jpgize_cmd, name="jpgize")
main.add_command(motionphotos_cmd, name="motionphotos")
main.add_command(mp4ize_cmd, name="mp4ize")
main.add_command(rename_cmd, name="renamers")
main.add_command(sidecars_cmd)

if __name__ == "__main__":
    main()
