"""Version info."""
import re
from collections import namedtuple
from typing import List

VersionInfo = namedtuple("VersionInfo", ["major", "minor", "micro", "releaselevel", "serial"])

# Version string must appear intact for hatch versioning
__version__ = "5.8.0"

# Build up version_info tuple for backwards compatibility
pattern = r"(?P<major>\d+).(?P<minor>\d+).(?P<micro>\d+)(?P<releaselevel>.*?)(?P<serial>\d*)"
match = re.match(pattern, __version__)
assert match is not None  # noqa
parts: List[object] = [int(match[part]) for part in ["major", "minor", "micro"]]
parts.append(match["releaselevel"] or "")
parts.append(match["serial"] or "")

version_info = VersionInfo(*parts)
