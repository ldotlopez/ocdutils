# -*- encoding: utf-8 -*-

from setuptools import setup


import datetime


setup(
    name='ocdutils',
    version='0.0.0.' + datetime.datetime.now().strftime('%Y%m%d%H%M%S'),
    author='Luis López',
    author_email='luis@cuarentaydos.com',
    packages=['ocdutils'],
    scripts=[],
    url='https://github.com/ldotlopez/ocdutils',
    license='LICENSE.txt',
    description=(
        'Utils for control your "Obsessive-Compulsive Disorder" with your data'
    ),
    long_description=open('README.md').read(),
    install_requires=[
        "piexif",
        "pillow"
    ],
    entry_points={
        'console_scripts':
            ['ocd-datetime=ocdutils.ocddatetime:main',
             'ocd-fslinter=ocdutils.ocdfslinter:main']
    }
)
