"""A project's direct dependencies, from pyproject.toml and requirements files."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

from packaging.requirements import InvalidRequirement, Requirement
from packaging.utils import canonicalize_name


@dataclass(frozen=True)
class Pin:
    name: str  # canonical, e.g. "typing-extensions"
    spec: str  # the version specifier, e.g. ">=1.2,<2" (may be empty)
    text: str  # the requirement as written
    source: str  # file it came from, relative to the project


def _parse(text: str, source: str) -> Pin | None:
    text = text.split(" #", 1)[0].strip()
    if not text or text.startswith(("#", "-")):
        return None  # comments and pip options (-r, -e, --index-url)
    try:
        req = Requirement(text)
    except InvalidRequirement:
        return None
    return Pin(canonicalize_name(req.name), str(req.specifier), text, source)


def read_pins(root: str | Path) -> list[Pin]:
    root = Path(root)
    pins: list[Pin] = []
    py = root / "pyproject.toml"
    if py.is_file():
        data = tomllib.loads(py.read_text())
        for text in data.get("project", {}).get("dependencies", []):
            if pin := _parse(text, "pyproject.toml"):
                pins.append(pin)
    for req in sorted(root.glob("requirements*.txt")):
        for line in req.read_text().splitlines():
            if pin := _parse(line, req.name):
                pins.append(pin)
    return pins


def find(pins: list[Pin], name: str) -> Pin:
    want = canonicalize_name(name)
    for p in pins:
        if p.name == want:
            return p
    raise ValueError(f"{name} is not a direct dependency of this project")
