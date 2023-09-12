import click

from . import filesystemfixes, formats, motionphotos, sidecars
from .similarity import cv2cmp, imagehashcmp


@click.group()
def main():
    pass


main.add_command(filesystemfixes.fix_extensions_cmd)
main.add_command(motionphotos.motionphoto_cmd)
main.add_command(imagehashcmp.find_duplicates_cmd)
main.add_command(sidecars.sidecars_cmd)
main.add_command(formats.formats_cmd)
# main.add_command(cv2cmp.calculate_cmd)
# main.add_command(cv2cmp.similarity_cmd)
# main.add_command(cv2cmp.group_cmd)