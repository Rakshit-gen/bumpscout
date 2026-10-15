"""Changing a pin in the file it was written in."""

from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet
from packaging.version import Version

from .pins import Pin


def proposed_spec(old: str, version: str) -> str:
    """The specifier to suggest for moving to `version`, in the style of the
    old one: an exact pin stays exact; otherwise the lower bound moves up and
    an upper bound that would exclude the new version moves to its next major.
    `~=` becomes a cap at the next major."""
    v = Version(version)
    specs = list(SpecifierSet(old))
    if not specs or any(s.operator in ("==", "===") for s in specs):
        return f"=={v}" if specs else f">={v}"
    out = [f">={v}"]
    for s in specs:
        if s.operator == "~=":  # a compatible-release cap, kept as a major cap
            out.append(f"<{v.major + 1}")
        elif s.operator in ("<", "<="):
            out.append(f"<{v.major + 1}" if not s.contains(v) else str(s))
        elif s.operator == "!=":
            out.append(str(s))
    return ",".join(out)


def requirement_text(pin: Pin, spec: str) -> str:
    req = Requirement(pin.text)
    req.specifier = SpecifierSet(spec)
    return str(req)


def set_pin(root: str | Path, pin: Pin, spec: str) -> str:
    """Rewrite `pin` in its file under `root` to use `spec`; returns the new
    requirement text."""
    path = Path(root) / pin.source
    text = path.read_text()
    new = requirement_text(pin, spec)
    if path.suffix == ".toml":
        new = new.replace('"', "'")  # it sits inside a double-quoted TOML string
    if pin.text not in text:
        raise ValueError(f"can't find {pin.text!r} in {pin.source}")
    path.write_text(text.replace(pin.text, new, 1))
    return new
