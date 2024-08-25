#! /usr/bin/env python3

#
#   This file is part of ZISA-X
#
#   SPDX-FileCopyrightText: 2024 Synthetic Dreams LLC <twestbrook@synthetic-dreams.com>
#
#   SPDX-License-Identifier: GPL-3.0-only
#


import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name='ZISA-X',
    version='1.0.0',
    author='Synthetic Dreams LLC',
    author_email='twestbrook@synthetic-dreams.com',
    packages=["images"],
    package_data={'': ['*']},
    scripts=['zisax.py'],
    include_package_data=True,
    url='http://github.com/ToniWestbrook/zisa-x',
    license='LICENSE',
    description='ZISA-X Z80 / ISA bus emulator',
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: POSIX :: Linux",
    ],
    install_requires=[
        'z80 @ git+https://github.com/kosarev/z80.git'
    ],
)
