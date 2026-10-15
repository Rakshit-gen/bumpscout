"""Reading release notes for names that went away."""

import re

from .index import Release

TICKED = re.compile(r"`([A-Za-z_][\w.]*)(?:\(\))?`")
GONE = re.compile(r"\b(remov\w*|renam\w*|is now|deprecat\w*|gone|no longer|dropp\w*)\b", re.I)


def changed_names(notes: str) -> list[str]:
    """Names in backticks on lines that say something was removed, renamed
    or deprecated, in order, without repeats. A plain keyword match: notes
    that say "removed" about something else still count."""
    out: list[str] = []
    for line in notes.splitlines():
        if GONE.search(line):
            for name in TICKED.findall(line):
                if name not in out:
                    out.append(name)
    return out


def combined(releases: list[Release]) -> str:
    """The notes of several releases, newest first, each under its version."""
    parts = []
    for r in reversed(releases):
        body = r.notes.strip() or "(no release notes)"
        if not body.lstrip("#").strip().startswith(r.version):
            body = f"## {r.version}\n{body}"
        parts.append(body)
    return "\n\n".join(parts)
