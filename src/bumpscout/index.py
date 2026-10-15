"""Where versions and release notes come from.

A fixture index is a folder: <package>/<version>/meta.json and notes.md, plus
the package's source under <package>/<version>/src. Scenarios use it so
nothing is downloaded. The live index is PyPI (see pypi.py).
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version


@dataclass
class Release:
    version: str
    requires_python: str = ""
    requires: list[str] = field(default_factory=list)
    yanked: bool = False
    notes: str = ""  # may be empty when the index has none


class Index(Protocol):
    def releases(self, name: str) -> list[Release]:
        """Every release of `name`, oldest first. Raises ValueError if unknown."""


def by_version(releases: list[Release]) -> list[Release]:
    def key(r: Release):
        try:
            return (0, Version(r.version))
        except InvalidVersion:
            return (-1, Version("0"))

    return sorted(releases, key=key)


def between(releases: list[Release], old: str, new: str) -> list[Release]:
    """Releases after `old` up to and including `new`."""
    lo, hi = Version(old), Version(new)
    return [r for r in releases if lo < Version(r.version) <= hi]


class FixtureIndex:
    def __init__(self, root: str | Path):
        self.root = Path(root)

    def _dir(self, name: str) -> Path:
        want = canonicalize_name(name)
        for d in self.root.iterdir() if self.root.is_dir() else []:
            if d.is_dir() and canonicalize_name(d.name) == want:
                return d
        raise ValueError(f"{name} is not in the index")

    def releases(self, name: str) -> list[Release]:
        out = []
        for v in self._dir(name).iterdir():
            if not (v / "meta.json").is_file():
                continue
            meta = json.loads((v / "meta.json").read_text())
            notes = (v / "notes.md").read_text() if (v / "notes.md").is_file() else ""
            out.append(
                Release(
                    v.name,
                    meta.get("requires_python", ""),
                    meta.get("requires", []),
                    meta.get("yanked", False),
                    notes,
                )
            )
        return by_version(out)

    def source(self, name: str, version: str) -> Path:
        """The folder whose contents go on the import path for this release."""
        src = self._dir(name) / version / "src"
        if not src.is_dir():
            raise ValueError(f"{name} {version} is not in the index")
        return src
