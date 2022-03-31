# Copyright (c) Jupyter Development Team.
# Distributed under the terms of the Modified BSD License.

from collections import namedtuple

VersionInfo = namedtuple("VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])

version_info = VersionInfo(5, 5, 1, "", "")

__version__ = f"{version_info.major}.{version_info.minor}.{version_info.micro}"

if version_info.releaselevel:
    __version__ += f"{version_info.releaselevel}{version_info.serial}"
