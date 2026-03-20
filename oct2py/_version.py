"""Version info."""

import re
from collections import namedtuple
from importlib.metadata import version as _version_metadata

VersionInfo = namedtuple("VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])

__version__ = _version_metadata("oct2py")

# Build up version_info tuple for backwards compatibility
pattern = r"(?P<major>\d+).(?P<minor>\d+).(?P<micro>\d+)(?P<releaselevel>.*?)(?P<serial>\d*)"
match = re.match(pattern, __version__)
assert match is not None  # noqa
parts: list[object] = [int(match[part]) for part in ["major", "minor", "micro"]]
parts.append(match["releaselevel"] or "")
parts.append(match["serial"] or "")

version_info = VersionInfo(*parts)
